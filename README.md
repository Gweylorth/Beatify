Beatify
=======

What for ?
----------
PHP BDD framework Behat generates HTML reports of its tests results. With Behat/Mink tests integrated 
in a Jenkins CI multi-configuration job, we get a whole lot of HTML reports, one for each config -
Firefox on Linux, on Windows, IE6, IE8, Chrome... - and we'd like to compress them all into one global
report, showing which tests failed on which config.
That's what Beatify does.

How does it work ?
------------------
It uses the LXML.HTML library to parse each report and build a new one, based on the first it found.
Then, it zips the informations for this build : global report, config reports and failings screenshots.

Why did I do that ?
-------------------
During my internship at Jouve ITS I had to try several BDD approaches (mainly jBehave and Behat/Mink).
We finally picked Behat and plugged it into Jenkins CI, but since we had many different configuration
profiles to test, we ended up with 10 reports for each build. Those weren't practical for sharing (which
is quite important in BDD), so I wrote this tool to get them all in one.