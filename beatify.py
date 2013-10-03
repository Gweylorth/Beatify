#!/usr/bin/python
# -*- coding: utf-8 -*-

''' Beatify, a Behat HTML Reports condenser
Author : Gwenegan Hudin <gwenegan.hudin@insa-rennes.fr>

Originally made to merge all reports under a Jenkins multi-configuration Behat job into one,
pointing out which steps/scenarios failed over any of the profiles, and the list of failing
profiles for each step.

Just run python beatify.py in Jenkins project's workspace root.

WARNING : This script needs lxml to be run.
You can get it by running "sudo apt-get install python-lxml" on Ubuntu.
'''

import os
import sys
import zipfile
try: 
    from lxml.html import parse, etree, tostring
except ImportError:
    sys.exit("Missing \"lxml\" dependancy. Please install it and try again.")

profiles = os.listdir('profile')
failed_steps = []
failed_scenarios = []

# Get which scenario this step is in
def get_ancestor_scenario(step):
    for ancestor in step.iterancestors():
        if ancestor.tag != 'div':
            continue
        tag_class = ancestor.attrib['class']
        if ('scenario' in tag_class or 'scenario outline' in tag_class or 
            'scenario background' in tag_class):
            return ancestor

# Keep trace of which and how many scenarios/steps failed over all profiles
def update_counters(failed_step):
    global failed_steps
    global failed_scenarios

    if not failed_step in failed_steps:
        failed_steps.append(failed_step)

    scenario = get_ancestor_scenario(failed_step)

    if not scenario in failed_scenarios:
        failed_scenarios.append(scenario)


# Simply copy the first report, it will be our starting point
tree = parse('profile/' + profiles[0] + '/reports/' + 'report_' + profiles[0] + '.html')

# Store each and every example case (passed or failed)
cases = tree.xpath('//tr[@class="passed"] | //tr[@class="failed"] | //li[@class="passed"] | //li[@class="failed"]')

# For each example, check if it is failed
for case in cases:

    # Prepare the list entry for this profile
    entry_setup = etree.Element('li')
    entry_setup.text = profiles[0]

    # Skip passed steps
    if case.attrib['class'] == 'passed':
        continue

    # Is it a standalone fail step ?
    standalone = case.tag == 'li'

    # Create the list of failing browsers
    browser_list = etree.Element('ul')
    browser_list.insert(0, entry_setup)
    
    if standalone:
        # Replace the "pre" tag by a new "div" with the failing browsers list
        error = case.find('pre')
        fail_div = etree.Element('div')
        fail_div.insert(0, browser_list)
        case.replace(error, fail_div)

    else:
        fail_row = case.getnext()
        cell = fail_row.find('td')
        # Get the stacktrace info
        error = cell.find('pre[@class="backtrace"]')
        # Create the list of the failing browsers
        browser_list = etree.Element('ul')
        browser_list.insert(0, entry_setup)
        cell.insert(0, browser_list)
        entry_setup.insert(0, error)

    # Add error info
    if error == None:
            error = etree.Element('pre', {'class':'backtrace'})
            error.text = 'No info'
    entry_setup.insert(0, error)

    # Update counters
    update_counters(case)



# For each remaining profile folder, parse its report. If no report found, pass
for profile in profiles[1:]:
    try:
        report = parse('profile/' + profile + '/reports/' + 'report_' + profile + '.html')
    except IOError:
        continue

    # Get all examples (in scenario outlines)
    examples = report.xpath('//div[@class="examples"]')

    # Store this profile's example cases
    profilecases = report.xpath('//tr[@class="passed"] | //tr[@class="failed"] | //li[@class="passed"] | //li[@class="failed"]')

    for i in range(0, len(profilecases)):
        # Prepare the list entry for this profile
        entry = etree.Element('li')
        entry.text = profile

        # Is it a standalone fail step ?
        standalone = profilecases[i].tag == 'li'

        if 'passed' in cases[i].attrib['class'] and 'failed' in profilecases[i].attrib['class']:
            parent = cases[i].getparent()

            # Create the list of failing browsers
            browser_list = etree.Element('ul')
            browser_list.insert(0, entry)
            
            if standalone:
                # Replace the "pre" tag by a new "div" with the failing browsers list
                error = profilecases[i].find('pre')
                fail_div = etree.Element('div')
                fail_div.insert(0, browser_list)
                profilecases[i].replace(error, fail_div)

            else:
                # Get the error message
                error = profilecases[i].getnext().find('td/pre[@class="backtrace"]')
                # Create the "failed exception" row
                fail_row = etree.Element('tr', {'class':'failed exception'})
                # Create the container cell 
                cell = etree.Element('td', colspan='2')
                # Insert list in the cell
                cell.insert(0, browser_list)
                # Insert the cell in the row
                fail_row.insert(0, cell)
                parent.insert(parent.index(cases[i]) + 1, fail_row)

            # Add error info
            if error == None:
                    error = etree.Element('pre', {'class':'backtrace'})
                    error.text = 'No info'
            entry.insert(0, error)

            # Update the original tree
            parent.replace(cases[i], profilecases[i])
            cases[i] = profilecases[i]
            update_counters(cases[i])

        elif 'failed' in cases[i].attrib['class'] and 'failed' in profilecases[i].attrib['class']:
            if standalone:
                # Get the new error and insert it
                error = profilecases[i].find('pre')
                entry.insert(0, error)
                # Get "failed" div (last child) and update its failing browsers list
                fail_div = cases[i][len(cases[i])-1]
                browser_list = fail_div.find('ul')
                browser_list.insert(len(browser_list), entry)
            else:
                # Get the error message, there can be no error message on the original report !
                error = profilecases[i].getnext().find('td/pre[@class="backtrace"]')
                if error == None:
                    error = etree.Element('pre', {'class':'backtrace'})
                    error.text = 'No info'
                entry.insert(0, error)
                # Get "failed exception" row (nearest sibling) and update its failing browser list
                fail_row = cases[i].getnext()
                cell = fail_row.find('td')
                browser_list = cell.find('ul')
                browser_list.insert(len(browser_list), entry)

            update_counters(cases[i])



# Update Test summary
if len(failed_steps):

    # Let's factorize the code
    def update_summary_part(counter, failings):
        total = int(counter.text.split()[0])
        counts = counter.findall('strong')

        # Update failed counter
        # If in the base report everything passed
        if len(counts) == 1:
            failed = etree.Element('strong', {'class':'failed'})
            failed.text = str(len(failings)) + ' echecs'
            counts[0].addnext(failed)
            counts[0].tail = ', '

        else:
            failed = counts[len(counts)-1]
            failed.text = str(len(failings)) + ' ' + failed.text.split()[1]

        # If there are skipped steps, remove those from the total
        if len(counts) == 3:
            total -= int(counts[1].text.split()[0])

        # Update succeeded counter
        success = counts[0]
        success.text = str(total - len(failings)) + " " + success.text.split()[1]


    counters = tree.xpath('//div[@class="counters"]')[0]

    # Pass from "summary passed" to "failed" if necessary
    summary = counters.getparent()
    if 'passed' in summary.attrib['class']:
        summary.attrib['class'] = 'summary failed'

    # Update scenario counters
    sce_counter = counters.find('p[@class="scenarios"]')
    update_summary_part(sce_counter, failed_scenarios)

    # Update step counters
    step_counter = counters.find('p[@class="steps"]')
    update_summary_part(step_counter, failed_steps)


# Edit report style to restrain error message's size
style = tree.getroot().find('head/style')
properties = ''' 

.backtrace {
    max-height: 100px;
    width: 800px;
    overflow:auto;
}
'''
style.text += properties

# Write global report
with open('global_report.html', 'w+') as final_report_file:
    final_report_file.write(tostring(tree))

# Let's zip it all ! And clean the workspace
with zipfile.ZipFile('latest_reports.zip', 'w') as myzip:
    myzip.write('global_report.html')
    os.remove('global_report.html')
    for root, dirs, files in os.walk('profile'):
        for file in files:
            myzip.write(os.path.join(root, file))
            # Clean screenshots
            if '.png' in file:
                os.remove(os.path.join(root, file))
