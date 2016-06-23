# fdbtest
Tool for testing firebird-driven databases

## Requirements

At the moment script requires python3 and [fdb](https://pypi.python.org/pypi/fdb) for its work. Also, you obviously should have access to firebird server - on the same mashine or somewhere else.

In debian-based systems all the necessary software can be installed by the command

 aptitude install python3 fdb firebird2.5-super

## Installation

After installing requirements script is self-sufficient and does not require any additional setup. You can download it into any suitable location and run using python3 interpreter.

## Running

When run without any params or with -h script shows all available options. Typical command line might look like this

 python3 fdbtest.py -s 192.168.1.1 -d employee -user sysdba -pass changed_masterkey -t dir_with_tests -r dir_with_results

## Test contents

Every test is described in a separate file in a JSON format with a following structure:
```json
{
  "id": "001",
  "name": "first test",
  "author": "developer",
  "description": "This is description of a test.",
  "testdata_files": ["test1.sql"],
  "test_files": ["test1.sh"],
  "test_statements": [
    {"sql": "select 1 as t1, 1 as t2, 1 as t3 from rdb$database", 
     "expect_values": {"t1": "1"},
     "expect_equals": ["t1", "t2", "t3"]
    }
}

```
