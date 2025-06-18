import mock

GLOBAL_RESULTS = {
    'select * from laboratoria order by kolejnosc': (
        ['symbol', 'nazwa', 'adres_fresh', 'aktywne'],
        [
            ['CZERNIA', 'lab1', '0.0.0.1', True],
            ['KOPERNI', 'lab2', '0.0.0.2', True],
            ['SIEDLCE', 'lab3', '0.0.0.3', True],
            ['RUDKA', 'lab4', '0.0.0.4', True],
            ['CZD', 'lab5', '0.0.0.5', False],
        ]
    )
}


class CursorDescMock:
    def __init__(self, name):
        self.name = name


class PostgresMock:
    def __init__(self, config):
        self.config = config
        self.next_result = None

    def execute_side_effect(self, query, params):
        if query in self.config.queries:
            self.next_result = self.config.queries[query]
        elif query in GLOBAL_RESULTS:
            self.next_result = GLOBAL_RESULTS[query]
        elif params is not None and params in self.config.queries:
            self.next_result = self.config.queries[params]
        elif self.config.default is not None:
            self.next_result = self.config.default
        else:
            raise ValueError('No prepared response for query', query, params)
        if self.next_result is not None:
            col_desc = [CursorDescMock(n) for n in self.next_result[0]]
            self.psycopg.return_value.cursor.return_value.description = col_desc

    def fetchall_side_effect(self):
        res = self.next_result[1]
        self.next_result = None
        return res

    def __enter__(self):
        self.psycopg = mock.patch('psycopg2.connect').__enter__()
        self.psycopg.return_value.cursor.return_value.execute.side_effect = self.execute_side_effect
        self.psycopg.return_value.cursor.return_value.fetchall.side_effect = self.fetchall_side_effect
        # przy okazji mockujemy redisa żeby nic nie zwracał - żeby nie było kasowania
        self.redis = mock.patch('helpers.widget_data.redis_conn').__enter__()
        self.redis.get.return_value = None
        self.redis.set.return_value = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.redis.__exit__(exc_type, exc_val, exc_tb)
        self.psycopg.__exit__(exc_type, exc_val, exc_tb)


class with_mocked_postgres:
    def __init__(self, queries=None, default=None):
        if queries is None:
            queries = []
        self.queries = queries
        self.default = default

    def __call__(self, test_function):
        def wrapper(*args, **kwargs):
            with PostgresMock(self):
                test_function(*args, **kwargs)

        return wrapper
