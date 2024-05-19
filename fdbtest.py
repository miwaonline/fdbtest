import os
import fdb  # requires external package
import logging
import argparse
import yaml  # required external package
import subprocess
import sys
import time

opt = 0
log = 0
fb = 0


class FBTOptions:
    """
    Place to share all common/global options including passed via command line
    """

    def __init__(self):
        """
        During initialization process command line arguments
        """
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-s",
            "--server",
            help="server host (default 127.0.0.1)",
            default="127.0.0.1",
        )
        parser.add_argument(
            "--port", help="server port (default 3050)", default=3050
        )
        parser.add_argument(
            "-d",
            "--database",
            help="database file or alias to use for testing",
            required=True,
        )
        parser.add_argument(
            "-u",
            "--username",
            help="username for access to FB server (default SYSDBA)",
            default="SYSDBA",
        )
        parser.add_argument(
            "-p",
            "--password",
            help="password for given username (default masterkey)",
            default="masterkey",
        )
        parser.add_argument(
            "-b", "--use_backup", help="restore given backup file for testing"
        )
        parser.add_argument(
            "-n",
            "--no_test_data",
            help="dont process test data files from tests",
            action="store_true",
            default=False,
        )
        parser.add_argument(
            "-t",
            "--run_test",
            help="run given test or all tests from given directory",
            required=True,
        )
        parser.add_argument(
            "-i",
            "--isql",
            help=(
                'isql binary (default is "isql-fb" for linux'
                ' and "isql.exe" for windows)'
            ),
            default="",
        )
        parser.add_argument(
            "-g",
            "--gbak",
            help=(
                'gbak binary (default is "gbak" for linux'
                ' and "gbak.exe" for windows)'
            ),
            default="",
        )
        parser.add_argument(
            "-r",
            "--results_dir",
            help=(
                "directory to store detailed information about"
                " executing tests"
            ),
        )
        parser.add_argument(
            "-f",
            "--force_clean",
            action="store_true",
            help=(
                "remove .log files from directory with results"
                " before executing tests"
            ),
        )
        self.cmdargs = parser.parse_args()
        # now set proper gbak and isql values
        if self.cmdargs.gbak == "":
            if os.name == "posix":
                self.cmdargs.gbak = "gbak"
            else:
                self.cmdargs.gbak = "gbak.exe"
        if self.cmdargs.isql == "":
            if os.name == "posix":
                self.cmdargs.isql = "isql-fb"
            else:
                self.cmdargs.isql = "isql.exe"


class FBTLog:
    """
    Place to keep loggging
    """

    def __init__(self, opt):
        if sys.stdout.isatty():
            formatter = logging.Formatter(
                fmt="%(asctime)s %(message)s", datefmt="%H:%M:%S"
            )
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logstd = logging.getLogger("stdout")
            logstd.setLevel(logging.INFO)
            logstd.addHandler(handler)
        else:
            logstd = logging.getLogger("dummy")

        if opt.cmdargs.results_dir:
            if opt.cmdargs.force_clean and os.path.exists(
                opt.cmdargs.results_dir
            ):
                for file in os.scandir(opt.cmdargs.results_dir):
                    if file.name.endswith(".log"):
                        os.remove(file.path)
            if not os.path.exists(opt.cmdargs.results_dir):
                os.makedirs(opt.cmdargs.results_dir)
            logfilename = opt.cmdargs.results_dir + os.sep + "fdbtest.log"
        else:
            logfilename = "fdbtest.log"

        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(message)s",
            datefmt="%Y/%m/%d %H:%M:%S",
        )
        handler = logging.FileHandler(logfilename)
        handler.setFormatter(formatter)
        logfile = logging.getLogger("logfile")
        logfile.setLevel(logging.INFO)
        logfile.addHandler(handler)

        self.stdout = logstd
        self.file = logfile


class Firebird:
    """
    Implements database processing
    """

    def __init__(self):
        """
        Initializing default connection params
        """
        self.username = "SYSDBA"
        self.password = "masterkey"
        self.database = "employee"
        self.host = "127.0.0.1"
        self.port = 3050
        self.charset = "UTF8"

    def Connect(
        self,
        database,
        username="SYSDBA",
        password="masterkey",
        host="127.0.0.1",
        port=3050,
        charset="UTF8",
    ):
        """
        Connect to database with the params provided
        """
        self.username = username
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.charset = charset
        self.db = fdb.connect(
            user=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
            charset=self.charset,
        )

    def Execute(self, statement, params=None):
        """
        Executes statement and returns dict with corresponding values or tulip with
        error information (error string, deprecated sql error code, gds error code)
        """
        cur = self.db.cursor()
        noresset = (
            "Attempt to fetch row of results after statement that does"
            " not produce result set."
        )
        try:
            cur.execute(statement, params)
            res = cur.fetchonemap()
            cur.transaction.commit()
        except fdb.Error as fdberror:
            if fdberror.args[0] == noresset:
                cur.transaction.commit()
                cur.close()
                res = dict()
            else:
                cur.transaction.rollback()
                cur.close()
                res = fdberror.args
        except Exception as error:
            cur.transaction.rollback()
            cur.close()
            res = error.args
        finally:
            return res


class Adds:
    def IsDigit(value):
        try:
            float(value)
            return True
        except ValueError:
            return False


class SingleTest:
    """
    Processes a single test file
    """

    def __init__(self, filename):
        """
        Create the necessary object from given yaml
        """
        with open(filename, mode="r", encoding="utf-8") as f:
            # self.fullYaml = yaml.safe_load(f)
            self.__dict__ = yaml.safe_load(f)

    def StoreRes(self, datastring):
        if opt.cmdargs.results_dir:
            with open(
                opt.cmdargs.results_dir + os.sep + self.id + ".log",
                mode="a",
                encoding="utf-8",
            ) as f:
                f.write(datastring + "\n" + ("=" * 80) + "\n")

    def CompareValues(self, received, expected):
        if Adds.IsDigit(expected) and Adds.IsDigit(received):
            return float(received) == float(expected)
        elif (
            (expected[:1] == ">")
            and Adds.IsDigit(received)
            and Adds.IsDigit(expected[1:])
        ):
            return float(received) > float(expected[1:])
        elif (
            (expected[:1] == "<")
            and Adds.IsDigit(received)
            and Adds.IsDigit(expected[1:])
        ):
            return float(received) < float(expected[1:])
        else:
            return str(received) == str(expected)

    def ExecFile(self, filename):
        """
        Execute given file. '.sql' files are executing through isql with command line
        arguments that were passed to the script, others - run directly.
        Returns True if system's error code is 0 and False otherwise.
        """
        file_passed = False
        debug_str = ""
        ext = os.path.splitext(filename)[1]
        if ext == ".sql":
            cmd = [
                opt.args.isql,
                f"{opt.args.server}/{opt.args.port}:{opt.args.database}",
                "-u",
                opt.args.username,
                "-pas",
                opt.args.password,
                "-i",
                filename,
                "-m",
                "-e",
            ]
            debug_str = (
                "Exexuting sql script using following command:\n"
                + " ".join(cmd)
            )
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            res = p.communicate()
            debug_str += "\n" + ("-" * 80) + "\n" + "".join(res[0]) + ("-" * 80)
            if p.returncode == 0:
                file_passed = True
                debug_str += "\nPASSED"
            else:
                log.file.error(
                    f"Error executing sql script {filename} with command line {cmd}"
                )
                debug_str += "\nFAILED"
        else:
            debug_str = f"Executing {filename} via system shell "
            p = subprocess.Popen(
                filename, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            res = p.communicate()
            if p.returncode == 0:
                file_passed = True
                debug_str += "\nPASSED"
            else:
                log.file.error(
                    f"Error executing file {filename} with error {p.returncode}"
                )
                debug_str += f"\nCommand returned error {p.returncode}"
                debug_str += "\nFAILED"
        self.StoreRes(debug_str)
        return file_passed

    def ExecStatement(self, statement, test_vars):
        stmt_passed = False
        debug_str = self._prepare_debug_str(statement, test_vars)

        # Fill parameters with their values
        paramlist = self._prepare_param_list(statement, test_vars)

        # Execute statement and measure execution time
        timestart = time.perf_counter()
        res = self._execute_statement(statement, paramlist)
        timefinish = time.perf_counter()

        # Check the results
        stmt_passed, debug_str = self._check_results(
            statement,
            res,
            test_vars,
            debug_str,
            timestart,
            timefinish,
            paramlist,
        )

        # Store and return results
        self.StoreRes(debug_str)
        return stmt_passed

    def _prepare_debug_str(self, statement, test_vars):
        debug_str = "### Statement:\n"
        debug_str += yaml.dump(statement, allow_unicode=True, sort_keys=False)
        debug_str += "\n### Variables:\n"
        debug_str += yaml.dump(test_vars, allow_unicode=True, sort_keys=False)
        return debug_str

    def _prepare_param_list(self, statement, test_vars):
        paramlist = []
        if statement.get("params"):
            for param in statement.get("params"):
                paramlist.append(test_vars[param.upper()])
        return paramlist

    def _execute_statement(self, statement, paramlist):
        if type(statement.get("sql")) is list:
            res = fb.Execute(" ".join(statement.get("sql")), paramlist)
        else:
            res = fb.Execute(statement.get("sql"), paramlist)
        return res

    def _check_results(
        self,
        statement,
        res,
        test_vars,
        debug_str,
        timestart,
        timefinish,
        paramlist,
    ):
        stmt_passed = True
        if type(res) is tuple and len(res) == 3:
            stmt_passed = self._handle_error(statement, res)
            debug_str += "\n### Results:\n" + " ".join(str(r) for r in res)
        else:
            stmt_passed = self._handle_success(statement, res, test_vars)
            debug_str += "\n### Results:\n" + str(res)

        if stmt_passed and statement.get("expect_duration"):
            stmt_passed, debug_str = self._check_duration(
                statement, timestart, timefinish, debug_str
            )

        if stmt_passed:
            debug_str += "\nPASSED"
        else:
            debug_str += "\nFAILED"
            log.file.error(
                f"Error while executing statement: {statement.get('sql')} with"
                f" params {paramlist}. {res}"
            )

        return stmt_passed, debug_str

    def _handle_error(self, statement, res):
        stmt_passed = False
        subtest_failed = False
        if statement.get("expect_error_gdscode"):
            if str(res[2]) == statement.get("expect_error_gdscode"):
                stmt_passed = True
            else:
                subtest_failed = True
        if not subtest_failed and statement.get("expect_error_string"):
            if str(res[0]).find(statement.get("expect_error_string")) > -1:
                stmt_passed = True
            else:
                stmt_passed = False
        return stmt_passed

    def _handle_success(self, statement, res, test_vars):
        stmt_passed = True
        for item in res:
            test_vars[item] = str(res.get(item))

        if statement.get("expect_values"):
            for exp in statement.get("expect_values"):
                exp_value = statement.get("expect_values")[exp]
                res_value = str(test_vars[exp.upper()])
                stmt_passed = stmt_passed and self.CompareValues(
                    res_value, exp_value
                )

        if stmt_passed and statement.get("expect_equals"):
            for i in range(len(statement.get("expect_equals")) - 1):
                v1 = statement.get("expect_equals")[i]
                v2 = statement.get("expect_equals")[i + 1]
                v1 = test_vars[v1.upper()]
                v2 = test_vars[v2.upper()]
                stmt_passed = stmt_passed and self.CompareValues(v1, v2)

        return stmt_passed

    def _check_duration(self, statement, timestart, timefinish, debug_str):
        stmt_passed = True
        timelength = timefinish - timestart
        if timelength > float(statement.get("expect_duration")):
            stmt_passed = False
            debug_str += (
                f"\nTimeout: statement executed {timelength:f} seconds"
                f"while expected {statement.get('expect_duration')}."
            )
        return stmt_passed, debug_str

    def RunTest(self):
        """
        Running main test files and statements
        """
        test_passed = True
        test_vars = {}
        if hasattr(self, "test_files"):
            self.StoreRes("Executing test files")
            for filename in self.test_files:
                test_passed = test_passed and self.ExecFile(filename)
        if hasattr(self, "test_statements"):
            self.StoreRes("Processing test statements")
            for statement in self.test_statements:
                test_passed = test_passed and self.ExecStatement(
                    statement, test_vars
                )
        return test_passed

    def RunFulltest(self):
        """
        Running all test routines
        """
        global log
        reset = "\x1b[0m"
        red = "\x1b[31;20m"
        grey = "\x1b[38;20m"
        yellow = "\x1b[33;20m"
        green = "\x1b[32;20m"
        # self.StoreRes(self.__dics__)
        if hasattr(self, "data_files") and not opt.args.no_test_data:
            log.stdout.info(f"{yellow}Preparing{reset} data for test "
                            f"No{self.id} {self.name}")
            log.file.info(f"Preparing data for test No{self.id} {self.name}")
            for filename in self.data_files:
                self.StoreRes(f"Processing data_file {filename}")
                self.ExecFile(filename)
        log.file.info(f"Running test No {self.id} {self.name}")
        if self.RunTest():
            log.stdout.info(f"{green}Passed{reset}: {self.id}, {self.name}")
            log.file.info(f"Passed: {self.id}, {self.name}")
        else:
            log.stdout.info(f"{red}Failed{reset}: {self.id}, {self.name}")
            log.file.info(f"Failed: {self.id}, {self.name}")


def restore_database(opt, log):
    log.file.info(
        f"Restoring database {opt.cmdargs.database} from backup file {opt.cmdargs.use_backup}"
    )
    cmd = [
        opt.cmdargs.gbak,
        "-rep",
        "-user",
        opt.cmdargs.username,
        "-pass",
        opt.cmdargs.password,
        opt.cmdargs.use_backup,
        opt.cmdargs.server
        + "/"
        + opt.cmdargs.port
        + ":"
        + opt.cmdargs.database,
    ]
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    p.communicate()
    if p.returncode != 0:
        log.file.error(
            f"Error restoring backup {opt.cmdargs.use_backup}"
            f" to database {opt.cmdargs.database}"
        )
        sys.exit(1)


def run_tests(opt, log):
    if os.path.isdir(opt.cmdargs.run_test):
        for filename in sorted(os.listdir(opt.cmdargs.run_test)):
            ext = os.path.splitext(filename)[1]
            if ext in (".yaml", ".yml"):
                atest = SingleTest(opt.cmdargs.run_test + os.sep + filename)
                atest.RunFulltest()
    elif os.path.isfile(opt.cmdargs.run_test):
        atest = SingleTest(opt.cmdargs.run_test)
        atest.RunFulltest()
    else:
        log.stdout.error(
            f"{opt.cmdargs.run_test} is neither file nor dir so nothing to run"
        )
        log.file.error(
            f"{opt.cmdargs.run_test} is neither file nor dir so nothing to run"
        )


def main():
    global log
    global opt
    global fb
    opt = FBTOptions()
    log = FBTLog(opt)
    log.file.info(f"Script invoked with {str(opt.cmdargs)}")
    if opt.cmdargs.use_backup:
        restore_database(opt, log)
    fb = Firebird()
    log.file.info(f"Connect to {opt.cmdargs.server}:{opt.cmdargs.database}")
    fb.Connect(
        opt.cmdargs.database,
        opt.cmdargs.username,
        opt.cmdargs.password,
        opt.cmdargs.server,
        opt.cmdargs.port,
    )
    run_tests(opt, log)


if __name__ == "__main__":
    main()
