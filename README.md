# fdbtest
Tool for testing firebird-driven databases

## Requirements and installation

At the moment script requires python3 and [fdb](https://pypi.python.org/pypi/fdb) for its work. Also, you obviously should have access to firebird server - on the same mashine or somewhere else.

In debian-based systems all the necessary software can be installed by the command
```bash
 apt install python3 fdb firebird3.0-server
```

In the case you already have a firebird server configured, you need to install python3 and then you can use `pip` to install additional python package:

```
pip3 install fdb
```

After installing requirements script is self-sufficient and does not require any additional setup. You can download it into any suitable location and run using python3 interpreter.

## Running

When run without any params or with -h script shows all available options. Typical command line might look like this
```bash
 python3 fdbtest.py -d employee -u sysdba -p masterkey -t dir_with_tests -r dir_with_results
```

The `examples` directory from this repository contains working set of tests that should be able to run on any Firebird database and provide some initial idea about how to write the tests.

## Test contents

Every test is described in a separate file in a JSON format with a following structure:
```json
{
  "id": "001",
  "name": "first test",
  "author": "developer",
  "description": "This is description of a test.",
  "data_files": ["test1.sql"],
  "test_files": ["test1.sh"],
  "test_statements": 
  [
    {"sql": "select 1 as t1, 1 as t2, 1 as t3 from rdb$database", 
     "expect_values": {"t1": "1"},
     "expect_equals": ["t1", "t2", "t3"]
    }
  ]
}

```
Items "id", "name", "author" and "description" are using just for idenifying a test and may contain any suitable information. Keep in mind, however, that in dir with results (if set) log files are created as "id".log.

"data_files" can be used for fullfilling database with a test data. Their executing can also be skipped with an option -n (-no_test_data) 

"test_files" can be used for testing. If set, they are executed in given order and expected to be finished with status code 0.

Files from both sections are running with firebird isql tool if they have .sql extension (you can also point out any particular binary through "-i" command line switch) and directly otherwise. This means that if you need to run some scripts during the test, you should have rights to execute them in your system.

"test_statements" is the core of testing tool. They consists of unlimited number of sections with the following items

 * "sql" - sql statement to be executed during the test
 * "expect_values" - list of values that are expected after executing mentioned statement. Simple comparisons like ">0" or "<10" can also be used.
 * "expect_equals" - list of variables, that are expected to be equal
 * "expect_error_gdscode" - GDS code of expected error. Test is considered as passed if this error occured after executing corresponding statement and failed otherwise
 * "expect_error_string" - string, that expected to be contained in raised error message. Test is considered as passed if error occured with appropriate message and failed in other case
 * "expect_duration" - floating number of seconds. Test is considered as failed if statement was executed longer that given number.
 * "params" - name of variables that will be used in the statement

### Variables
After executing every statement all results are stored with their corresponding names and can be used in subsequent statements for comparison or as a params. Lets look at the following example:
```json
  {"sql": "select 1 as t1, 100 as t2, 1 as t3 from rdb$database", 
   "expect_values": {"t1": "1", "t2": "100"},
   "expect_equals": ["t1", "t3"]
  }
```
After processing this block we'll get thee variables: "t1" and "t3" with value "1" and "t2" with value "100". Now we can not only compare them in the same section, but also use in the followings:
```json
 {"sql": "insert into table1(field1, field2) values (?, ?)",
 "params": ["t1", "t2"]
 }
```

## ToDo
- add YAML support for tests