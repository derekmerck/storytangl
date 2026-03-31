testsuite global:
    teardown:
        exit

    testcase lantern_road:
        run Jump("start")
        advance until screen "choice"
        click "Approach the waiting guide"
        advance until screen "choice"
        click "Take the lantern road"
        advance repeat 3

    testcase river_path:
        run Jump("start")
        advance until screen "choice"
        click "Approach the waiting guide"
        advance until screen "choice"
        click "Risk the river path"
        advance repeat 3

