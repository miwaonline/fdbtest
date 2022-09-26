# fdbtest
Tool for testing firebird-driven databases

## Requirements and installation

Script requires python3 for its work with a few additional packages - [fdb](https://pypi.python.org/pypi/fdb) to access Firebird databases and [pyyaml](https://pyyaml.org/) to process YAML files. Also, you obviously should have access to firebird server - on the same mashine or somewhere else.

In debian-based systems all the necessary software can be installed by the command

```bash
 apt install python3 firebird3.0-server python3-yaml python3-fdb
```

In the case you already have a firebird server handy, and some python3 ready-to-use, you can utilise `pip3` to install additional python package:

```
pip3 install fdb pyyaml
```

After installing requirements script is self-sufficient and does not require any additional setup. You can download it into any suitable location and run using python3 interpreter.

## Running the script

When run without any params or with -h script shows all available options. Typical command line might look like this

```bash
 python3 fdbtest.py -d employee -u sysdba -p masterkey -t dir_with_tests -r dir_with_results
```

If run from console (as in opposite to be run from `cron` or from other tool w/o stdout provided), it outputs plain "passed/failed" results for each test. In addition `fdbtest.log` is created either in `dir_with_results` if provided or in the current dir.

## Test contents

Every test is described in a separate file in YAML format with a following structure:

```yaml
---
id: "001"
name: "first test"
author: "developer"
description": "This is description of a test."
data_files": ["test1.sql"]
test_files": ["test1.sh"]
test_statements":
  - sql: "select 1 as t1, 1 as t2, 1 as t3 from rdb$database"
    expect_values: {"t1": "1"}
    expect_equals: ["t1", "t2", "t3"]
```

Items "id", "name", "author" and "description" are using just for idenifying a test and may contain any suitable information. Keep in mind, however, that in dir with results (if set) log files are created as "id".log.

"data_files" can be used for fullfilling (empty "golden") database with some testing data. Their executing can also be skipped with an option -n (-no_test_data) to address the case when a test usually requires some data but in the particular scenario the data already persist in the testing database.

"test_files" - some external scripts that can be used for testing. If set, they are executed in given order and expected to be finished with status code 0.

Files from both sections are executed by the firebird `isql` tool if they have .sql extension (you can also point out any particular binary through "-i" command line switch) and directly otherwise. This means that if you need to run some scripts during the test, you should have rights to execute them in your system.

"test_statements" is the core of testing tool. They consists of unlimited number of sections with the following items

 * "sql" - sql statement to be executed during the test
 * "expect_values" - list of values that are expected after executing mentioned statement. Simple comparisons like ">0" or "<10" can also be used.
 * "expect_equals" - list of variables, that are expected to be equal
 * "expect_error_gdscode" - GDS code of expected error. Test is considered as passed if this error occured after executing corresponding statement and failed otherwise
 * "expect_error_string" - string, that expected to be contained in raised error message. Test is considered as passed if error occured with appropriate message and failed in other case
 * "expect_duration" - floating number of seconds. Test is considered as failed if statement was executed longer that given number.
 * "params" - name of variables that will be used in the statement

For any test, all the items are optional, i.e. a test with only, lets say, `test_files` section is completely legit. Again, keep in mind, that if you provided `result_dir` command line switch, `id` has to be set.

For `test_statements` section, `sql` item is compulsory, all other items are optional.

### Variables
After executing every statement all results are stored with their corresponding names and can be used in subsequent statements for comparison or as a params. Lets look at the following example:

```yaml
  - sql: "select 1 as t1, 100 as t2, 1 as t3 from rdb$database"
    expect_values: {"t1": "1", "t2": "100"}
    expect_equals: ["t1", "t3"]
```

After processing this block we'll get thee variables: "t1" and "t3" with value "1" and "t2" with value "100". Now we can not only compare them in the same section, but also use in the followings:

```yaml
 - sql: "insert into table1(field1, field2) values (?, ?)",
   params: ["t1", "t2"]
```
### Examples

The `examples` directory from this repository contains working set of tests that should be able to run on any Firebird database and provide some initial idea about how to write the tests.

The `abacus` directory contains actual set of tests that are used in a live project with the same name for which this tool was actually developed. It will run on its own database only, but provides way more examples of the actual tool usage.
