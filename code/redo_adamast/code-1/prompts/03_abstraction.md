## WHAT CORRECT WORK LOOKS LIKE HERE
{field_analysis}

## FAILURE INSTANCES
{instances}

## TASK

Group the failure instances above into failure modes.

Put instances together when they are the same kind of wrong action. An
instance that matches nothing else still gets its own mode, as long as it
could recur.

The instances were written quickly and may be messy or described by their
effect. Look for the wrong action behind each one.

Every instance must end up in exactly one mode, or in "unplaced" with a
reason (for example, it describes an effect rather than a failure, or an
infrastructure problem). Do not drop any instance silently.

Name a mode's instances by their ids only, in "instance_ids", in place of
"instances". Do not copy the instances; they are attached by id afterwards.

Return ONLY JSON:
{"modes": [<failure modes in the FORMAT above, with "instance_ids": ["I3", "I17", ...]
            in place of "instances"; ids FM-01, FM-02, ...>],
 "unplaced": [{"instance_id": "...", "why": "..."}]}
