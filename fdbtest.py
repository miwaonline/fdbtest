#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import fdb #requires external package
import logging
import argparse
import json
import collections
import subprocess
import sys
import time

class Adds:
    def IsDigit(value):
        try:
            float(value)
            return True
        except ValueError:
            return False

class TestOptions:
    """
    Place to share all common/global options
    """
    def __init__(self):
        """
        During initialization process command line arguments
        """
        parser = argparse.ArgumentParser()
        parser.add_argument('-s', '--server', \
            help='server host (default 127.0.0.1)',\
            default='127.0.0.1')
        parser.add_argument('--port', \
            help='server port (default 3050)',\
            default='3050')
        parser.add_argument('-d', '--database', \
            help='database file or alias to use for testing',\
            required=True)
        parser.add_argument('-u', '--username', \
            help='username for access to FB server (default SYSDBA)',\
            default='SYSDBA')
        parser.add_argument('-p', '--password', \
            help='password for given username (default masterkey)',\
            default='masterkey')
        parser.add_argument('-b', '--use_backup', \
            help='restore given backup file for a testing')
        parser.add_argument('-n', '--no_test_data', \
            help='dont process test data files from tests', \
            action='store_true', default=False)
        parser.add_argument('-t', '--run_test', \
            help='run given test or all tests from given directory',\
            required=True)
        parser.add_argument('-i', '--isql',\
            help='isql binary (default is "isql-fb" for linux and "isql.exe" for windows)',\
            default='')
        parser.add_argument('-g', '--gbak',\
            help='gbak binary (default is "gbak" for linux and "gbak.exe" for windows)',\
            default='')
        parser.add_argument('-r', '--results_dir',\
            help='directory to store detailed information about executing tests')
        TestOptions.args = parser.parse_args()

class SingleTest:
    """
    Here all magic will be placed
    """
    def __init__(self, filename):
        """
        Create all the necessary from given filename
        """
        with open(filename, mode='r', encoding='utf-8') as f:
            self.__dict__ = json.load(f, object_pairs_hook=collections.OrderedDict)

    def StoreRes(self, datastring):
        if opt.args.results_dir:
            with open(opt.args.results_dir + os.sep + self.id + '.log', mode='a', \
                encoding='utf-8') as f:
                f.write(datastring + '\n' + ('=' * 80) + '\n')

    def CompareValues(self, received, expected):        
        if Adds.IsDigit(expected) and Adds.IsDigit(received):
            return float(received) == float(expected)
        elif (expected[:1] == '>') \
        and Adds.IsDigit(received) and Adds.IsDigit(expected[1:]):
            return float(received) > float(expected[1:])
        elif (expected[:1] == '<') \
        and Adds.IsDigit(received) and Adds.IsDigit(expected[1:]):
            return float(received) < float(expected[1:])
        else:
            return str(received) == str(expected)

    def ExecFile(self,filename):
        """
        Execute given file. '.sql' files are executing through isql with command line
        arguments that were passed to the script, others - run directly. 
        Returns True if system's error code is 0 and False otherwise.
        """
        file_passed = False
        debug_str = ''
        ext = os.path.splitext(filename)[1]
        if ext == '.sql':
            cmd = [opt.args.isql, \
                opt.args.server + '/' + opt.args.port + ':' + opt.args.database, \
                '-u', opt.args.username, '-pas', opt.args.password, \
                '-i', filename, '-m', '-e']
            debug_str = 'Exexuting sql script using following command:\n' + \
                ' '.join(cmd)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,\
                universal_newlines=True)
            res = p.communicate()
            debug_str += '\n' + ('-' * 80) + '\n' + ''.join(res[0]) + ('-' * 80)
            if p.returncode == 0:
                file_passed = True
                debug_str += '\nPASSED'
            else:
                logging.error('Error executing sql script {} with command line {}'.\
                    format(filename, cmd))
                debug_str += '\nFAILED'
        else:
            debug_str = 'Executing {} via system shell '.format(filename)
            p = subprocess.Popen(filename, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            res = p.communicate()
            if p.returncode == 0:
                file_passed = True
                debug_str += '\nPASSED'
            else:
                logging.error('Error executing file {} with error {}'.\
                    format(filename, p.returncode))
                debug_str += '\nCommand returned error {}'.format(p.returncode)
                debug_str += '\nFAILED'
        self.StoreRes(debug_str)
        return file_passed

    def ExecStatement(self, db, statement, test_vars):
        stmt_passed = False
        debug_str = json.dumps(statement, indent=2, \
            default=lambda o: o.__dict__, ensure_ascii=False)
        debug_str += '\n\nVariables: ' + \
            json.dumps(test_vars, default=lambda o: o.__dict__, ensure_ascii=False)
        #at first fill params with their values
        paramlist = []
        if not statement.get('params') is None:
            for param in statement.get('params'):
                paramlist.append(test_vars[param.upper()])
        #execute statement and measure execution time
        timestart = time.time()
        res = db.Execute(statement.get('sql'), paramlist)
        timefinish = time.time()
        #tuple with 3 items is standart fb error with items "errorstring",
        #deprecated "sqlcode" and "gdscode"; so we check both "expect_error_string"
        #and "expect_error_gdscode" (if set) to pass the test
        if type(res) is tuple and len(res) == 3:
            stmt_passed = False
            subtest_failed = False
            if not statement.get('expect_error_gdscode') is None:
                if str(res[2]) == statement.get('expect_error_gdscode'):
                    stmt_passed = True
                else:
                    subtest_failed = True
            if not (subtest_failed and statement.get('expect_error_string') is None):
                if str(res[0]).find(statement.get('expect_error_string')) > -1:
                    stmt_passed = True
                else:
                    stmt_passed = False
            debug_str += '\n\nResults:\n' + ' '.join(str(r) for r in res)
        else:
            for item in res:
                #force convert to str because in some cases interpreter tryes
                #to do smth like Decimal(1.5) and subsequently fails
                test_vars[item] = str(res.get(item))
            if len(res) > 0:
                debug_str += '\n\nResults:\n' + str(res)

            stmt_passed = True
            if statement.get('expect_values'):
                for exp in statement.get('expect_values'):
                    exp_value = statement.get('expect_values')[exp]
                    res_value = str(test_vars[exp.upper()])
                    stmt_passed = stmt_passed and self.CompareValues(res_value, exp_value)
            if stmt_passed and statement.get('expect_equals'):
                for i in range(len(statement.get('expect_equals')) - 1):
                    v1 = statement.get('expect_equals')[i]
                    v2 = statement.get('expect_equals')[i+1]
                    v1 = test_vars[v1.upper()]
                    v2 = test_vars[v2.upper()]
                    debug_str += '\nComparing values {} and {}'.format(v1, v2)
                    stmt_passed = stmt_passed and self.CompareValues(v1, v2)
        if stmt_passed and statement.get('expect_duration'):
            timelength = timefinish - timestart
            if timelength > float(statement.get('expect_duration')):
                stmt_passed = False
                debug_str += '\nTimeout: statement executed {:f} seconds while expected {}'\
                  .format(timelength, statement.get('expect_duration'))
        if stmt_passed:
            debug_str += '\nPASSED'
        else:
            logging.error("Error while executing statement: {} with params {}. {}"\
                .format(statement.get('sql'), paramlist, res))
            debug_str += '\nFAILED'
        self.StoreRes(debug_str)
        return stmt_passed

    def RunTest(self, db):
        """
        Running main test files and statements
        """
        test_passed = True
        test_vars = {}
        if hasattr(self, 'test_files'):
            self.StoreRes('Executing test files')
            for filename in self.test_files:
                test_passed = test_passed and self.ExecFile(filename)
        if hasattr(self, 'test_statements'):
            self.StoreRes('Processing test statements')
            for statement in self.test_statements:
                test_passed = test_passed and self.ExecStatement(db, statement, test_vars)
        return test_passed

    def RunFulltest(self, db):
        """
        Running all test routines
        """
        self.StoreRes(json.dumps(self.__dict__, indent=2, \
            default=lambda o: o.__dict__, ensure_ascii=False))
        if hasattr(self, 'data_files') and not opt.args.no_test_data:
            logging.info("Preparing data for test No{} '{}'".format(self.id, self.name))
            for filename in self.data_files:
                self.StoreRes('Processing data_file {}'.format(filename))
                self.ExecFile(filename)
        logging.info("Running test No{} '{}'".format(self.id, self.name))
        if self.RunTest(db):
            print('Passed:', self.name)
            logging.info("Passed")
        else:
            print('Failed:', self.name)
            logging.info("Failed")

class Firebird:
    """
    Realises work with database
    """
    def __init__(self):
        """
        Initializing default connection params
        """
        self.username = 'SYSDBA'
        self.password = 'masterkey'
        self.database = 'employee'
        self.host = '127.0.0.1'
        self.port = '3050'
        self.charset = 'UTF8'

    def Connect(self, database, username='SYSDBA', password='masterkey', \
            host='127.0.0.1', port=3050, charset='UTF8'):
        """
        Connect to database with given params
        """
        self.username = username
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.charset = charset
        self.db = fdb.connect(user=self.username, password=self.password, \
                  host=self.host, port=self.port, \
                  database=self.database, charset=self.charset)

    def Execute(self, statement, params=None):
        """
        Executes statement and returns dict with corresponding values or tulip with
        error information (error string, deprecated sql error code, gds error code)
        """
        cur = self.db.cursor()
        try:
            cur.execute(statement, params)
            res = cur.fetchonemap()
            cur.transaction.commit()
        except fdb.Error as fdberror:
            if fdberror.args[0] == 'Attempt to fetch row of results after statement that does not produce result set.':
                cur.transaction.commit()
                cur.close()
                res = dict()
            else:
                cur.transaction.rollback()
                cur.close()
                res = fdberror.args
        except:
            cur.transaction.rollback()
            cur.close()
            res = fdberror.args
        finally:
            return res

if __name__ == '__main__':
    opt = TestOptions()
    if opt.args.results_dir:
        if not os.path.exists(opt.args.results_dir):
            os.makedirs(opt.args.results_dir)
        logging.basicConfig(filename=opt.args.results_dir + os.sep + 'logfile.log',\
            level=logging.INFO, \
            format='%(asctime)s %(levelname)s %(message)s', \
            datefmt='%Y/%m/%d %H:%M:%S')
    else:
        logging.basicConfig(filename='logfile.log',\
            level=logging.INFO, \
            format='%(asctime)s %(levelname)s %(message)s', \
            datefmt='%Y/%m/%d %H:%M:%S')

    if opt.args.use_backup:
        if opt.args.gbak == '':
            if os.name == 'posix':
                opt.args.gbak = 'gbak'
            else:
                opt.args.gbak = 'gbak.exe'
        cmd = [opt.args.gbak, '-rep', '-user', opt.args.username, \
            '-pass', opt.args.password, opt.args.use_backup, \
            opt.args.server + '/' + opt.args.port + ':' + opt.args.database]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,\
                universal_newlines=True)
        res = p.communicate()
        if p.returncode != 0:
            logging.error('Error restoring backup {} to database {}'.
                format(opt.args.use_backup, opt.args.database))
            sys.exit(1)

    if opt.args.isql == '':
        if os.name == 'posix':
            opt.args.isql = 'isql-fb'
        else:
            opt.args.isql = 'isql.exe'
    
    fb = Firebird()
    fb.Connect(opt.args.database, opt.args.username, opt.args.password, \
        opt.args.server, opt.args.port)

    if os.path.isdir(opt.args.run_test):
        for filename in sorted(os.listdir(opt.args.run_test)):
            ext = os.path.splitext(filename)[1]
            if ext == '.fbt':
                atest = SingleTest(opt.args.run_test + os.sep + filename)
                atest.RunFulltest(fb)
    elif os.path.isfile(opt.args.run_test):
        atest = SingleTest(opt.args.run_test)
        atest.RunFulltest(fb)
    else:
        print("{} is neither file nor dir so nothing to run".
            format(opt.args.run_test))
