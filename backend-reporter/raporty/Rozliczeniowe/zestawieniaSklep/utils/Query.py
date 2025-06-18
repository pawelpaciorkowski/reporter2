import copy
from datasources.mysql import MySQLDatasource


class QueryData:
    PARAMS_TO_SKIP = []

    def __init__(self, db: MySQLDatasource, query: str, query_params: str):
        self._db_connection = db
        self._query = query
        self._query_params = query_params
        self._get_data()

    def _get_data(self):
        if isinstance(self._query_params, dict):
            params = self.dic_params_to_list(self._query_params)
        else:
            params = self._query_params
        self._data = self._db_connection.dict_select(
            sql=self._query,
            params=params)

    @property
    def data(self):
        return self._data

    @property
    def params(self):
        return self._query_params

    @staticmethod
    def _params_to_list(params, params_to_skip):

        for p in params_to_skip:
            del params[p]
        return tuple([params[p] for p in params])

    def dic_params_to_list(self, query_params):
        params = copy.deepcopy(query_params)
        return self._params_to_list(params, self.PARAMS_TO_SKIP)


class TestAndExamineQueryData(QueryData):
    PARAMS_TO_SKIP = ['product_type']

    def __init__(self, db: MySQLDatasource, query: str, query_params: str):
        super().__init__(db, query, query_params)
