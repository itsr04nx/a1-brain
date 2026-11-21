#!/bin/bash
read -r PASSWORD
EXPECTED_SECRET="${COCKPIT_SSO_SECRET:-__REDACTED__}"

if [[ "$PAM_USER" == "admin" || "$PAM_USER" == "rohan" ]]; then
    if [[ "$PASSWORD" == "$EXPECTED_SECRET" ]]; then
        exit 0
    fi
fi
exit 1
