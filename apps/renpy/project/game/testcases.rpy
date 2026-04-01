testsuite global:
    teardown:
        exit

    testcase lantern_road:
        run Jump("start")
        advance until "Approach the waiting guide"
        click "Approach the waiting guide"
        advance until "Take the lantern road"
        click "Take the lantern road"
        advance repeat 3

    testcase river_path:
        run Jump("start")
        advance until "Approach the waiting guide"
        click "Approach the waiting guide"
        advance until "Risk the river path"
        click "Risk the river path"
        advance repeat 3
