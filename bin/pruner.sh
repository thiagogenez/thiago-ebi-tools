#!/usr/bin/env bash

find /scratch -user thiagogenez -not -path '*/\.*' -delete 2>/dev/null
