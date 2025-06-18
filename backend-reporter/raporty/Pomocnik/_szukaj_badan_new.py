from elasticsearch import Elasticsearch, NotFoundError
from config import Config


def szukaj_badania_w_labie(lab, is_bundle):
    dane_lab = {}
    es_client = Elasticsearch(
        Config.ES_BADANIA_URL,
        basic_auth=("elastic", Config.ES_BADANIA_KEY)
    )

    def szukaj_badania(query, required_fields):
        local_is_bundle = is_bundle
        print('SZUKAJ BADANIA', lab, query, required_fields)
        es_query = {
            "script_score": {
                "query":
                    {
                        "bool":
                            {
                                "must":
                                    [
                                        {
                                            "multi_match": {
                                                "query": query,
                                                "fields": ['name_pl^3', 'symbol^2', 'altnames^3', 'synonymes^2',
                                                           'info_comments^1'],
                                                "analyzer": "custom_synonym_analyzer"
                                            }
                                        }
                                    ]
                            }
                    },
                "script":
                    {
                        "id": "my_custom_score",
                        "params": {"queryText": query}
                    }
            }
        }
        if local_is_bundle is None:
            if 'pakiet' in query.lower() or 'panel' in query.lower():
                local_is_bundle = True
        if local_is_bundle is not None:
            es_query['script_score']['query']['bool']['must'].append(
                {
                    "term": {"is_bundle": "true" if local_is_bundle else "false"}
                }
            )

        resp = es_client.search(
            index='badania', query=es_query,
            size=10
        )
        hits = resp['hits']['hits']
        if len(hits) == 0:
            return None
        hit = hits[0]['_source']
        symbol = hit['symbol']
        res = {
            'symbol': symbol, 'nazwa': hit['name_pl'],
        }
        if symbol in dane_lab:
            for k, v in dane_lab[symbol]:
                res[k] = v
        return res


    return szukaj_badania
