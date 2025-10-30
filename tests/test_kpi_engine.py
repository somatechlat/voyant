import duckdb
from udb_api.kpi import execute_kpis


def test_execute_single_string():
    con = duckdb.connect(database=':memory:')
    con.execute("create table t(a int, b int);")
    con.execute("insert into t values (1,2),(3,4)")
    res = execute_kpis(con, "select count(*) as c from t")
    assert len(res) == 1
    assert res[0]['rows'][0][0] == 2


def test_execute_multiple_named():
    con = duckdb.connect(database=':memory:')
    con.execute("create table t(a int);")
    con.execute("insert into t values (1),(2),(3)")
    spec = [
        {"name": "cnt", "sql": "select count(*) as c from t"},
        {"name": "vals", "sql": "select a from t order by 1"}
    ]
    res = execute_kpis(con, spec)
    names = {r['name'] for r in res}
    assert {'cnt','vals'} <= names


def test_invalid_statement_blocked():
    con = duckdb.connect(database=':memory:')
    con.execute("create table t(a int);")
    try:
        execute_kpis(con, "delete from t")
    except ValueError:
        return
    assert False, "Should have raised ValueError for non-select"
