#! /usr/bin/env python

from __future__ import print_function

import glob
import json
import os

import jinja2
import xunitparser

from github import Github

pylintReportFile = 'pylint.jinja'
pylintSummaryFile = 'pylintSummary.jinja'
unitTestSummaryFile = 'unitTestReport.jinja'

reportWarnings = ['0611', '0612', '0613']

summaryMessage = ''
longMessage = ''
reportOn = {}
failed = False


def buildPylintReport(templateEnv):
    with open('pylintReport.json', 'r') as reportFile:
        report = json.load(reportFile)

        pylintReportTemplate = templateEnv.get_template(pylintReportFile)
        pylintSummaryTemplate = templateEnv.get_template(pylintSummaryFile)

        # Process the template to produce our final text.
        pylintReport = pylintReportTemplate.render({'report': report,
                                                    'filenames': sorted(report.keys()),
                                                    })
        pylintSummary = pylintSummaryTemplate.render({'report': report,
                                                      'filenames': sorted(report.keys()),
                                                      })

    # Figure out if pylint failed

    failed = False
    for filename in report.keys():
        for event in report[filename]['test']['events']:
            if event[1] in ['W', 'E']:
                failed = True

    return failed, pylintSummary, pylintReport


def buildTestReport(templateEnv):
    unstableTests = []
    testResults = {}

    try:
        with open('UnstableTests.txt') as unstableFile:
            for line in unstableFile:
                unstableTests.append(line.strip())
    except:
        print("Was not able to open list of unstable tests")

    for kind, directory in [('base', './MasterUnitTests/'), ('test', './LatestUnitTests/')]:
        for xunitFile in glob.iglob(directory + '*/nosetests-*.xml'):
            ts, tr = xunitparser.parse(open(xunitFile))
            for tc in ts:
                testName = '%s:%s' % (tc.classname, tc.methodname)
                if testName in testResults:
                    testResults[testName].update({kind: tc.result})
                else:
                    testResults[testName] = {kind: tc.result}

    failed = False
    errorConditions = ['error', 'failure']

    newFailures = []
    unstableChanges = []
    okChanges = []
    added = []
    deleted = []

    for testName, testResult in sorted(testResults.items()):
        oldStatus = testResult.get('base', None)
        newStatus = testResult.get('test', None)
        if oldStatus and newStatus and testName in unstableTests:
            if oldStatus != newStatus:
                unstableChanges.append({'name': testName, 'new': newStatus, 'old': oldStatus})
        elif oldStatus and newStatus:
            if oldStatus != newStatus:
                if newStatus in errorConditions:
                    failed = True
                    newFailures.append({'name': testName, 'new': newStatus, 'old': oldStatus})
                else:
                    okChanges.append({'name': testName, 'new': newStatus, 'old': oldStatus})
        elif newStatus:
            added.append({'name': testName, 'new': newStatus, 'old': oldStatus})
            if newStatus in errorConditions:
                failed = True
        elif oldStatus:
            deleted.append({'name': testName, 'new': newStatus, 'old': oldStatus})

    changed = newFailures or added or deleted or unstableChanges or okChanges
    stableChanged = newFailures or added or deleted or okChanges

    unitTestSummaryTemplate = templateEnv.get_template(unitTestSummaryFile)

    unitTestSummary = unitTestSummaryTemplate.render({'newFailures': newFailures,
                                                      'added': added,
                                                      'deleted': deleted,
                                                      'unstableChanges': unstableChanges,
                                                      'okChanges': okChanges,
                                                      'errorConditions': errorConditions,
                                                      })

    return failed, unitTestSummary


templateLoader = jinja2.FileSystemLoader(searchpath="templates/")
templateEnv = jinja2.Environment(loader=templateLoader, trim_blocks=True, lstrip_blocks=True)

failedPylint = False
failedUnitTests = False

with open('artifacts/PullRequestReport.html', 'w') as html:
    failedPylint, pylintSummary, pylintReport = buildPylintReport(templateEnv)
    html.write(pylintSummary)
    html.write(pylintReport)

    failedUnitTests, unitTestSummary = buildTestReport(templateEnv)

    html.write(unitTestSummary)

# gh = Github(os.environ['DMWMBOT_TOKEN'])
# codeRepo = os.environ.get('CODE_REPO', 'WMCore')
# repoName = '%s/%s' % (os.environ['WMCORE_REPO'], codeRepo)
