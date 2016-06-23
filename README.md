# fdbtest
Tool for testing firebird-driven databases

## Requirements

At the moment script requires python3 and [fdb](https://pypi.python.org/pypi/fdb) for its work. Also, you obviously should have access to firebird server - on the same mashine or somewhere else.

In debian-based systems all the necessary software can be installed by the command
```bash
 aptitude install python3 fdb firebird2.5-super
```
## Installation

After installing requirements script is self-sufficient and does not require any additional setup. You can download it into any suitable location and run using python3 interpreter.

## Running

When run without any params or with -h script shows all available options. Typical command line might look like this
```bash
 python3 fdbtest.py -d employee -u sysdba -p masterkey -t dir_with_tests -r dir_with_results
```
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
Items "id", "name", "author" and "description" are just for idenifying a test and may contain any suitable information. Keep in mind, however, that in dir with results (if set) log files are created as "id".log.

"data_files" are using for fullfilling database with a test data. 

"test_files" can be used for testing.

Files from both sections are running with firebird isql tool (you can also point out any particular binary through "-i" command line switch) if they have .sql extension and directly otherwise. That means that if you need to run some scripts during the test, you should have rights to execute them in the particular system.
