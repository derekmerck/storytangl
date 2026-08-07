# Hall Monitor

`hall_monitor` is the school conformance world for the reusable credentials
mechanic. It exposes a world-local `school` catalog, fixes that catalog on its
Hall Monitor scenario type, and lets the script configure one sampled morning
shift with a deterministic seed, disposition distribution, and recurring
student encounter.

The world keeps school vocabulary—student IDs, teacher signatures, doctor's
notes, and office referrals—in its catalog and presentation profile. The shared
credentials game still owns packet materialization, availability, inspection,
mediation, disposition resolution, scoring, and persistence.

Hall Monitor also demonstrates world-authored consequence return. Its recurring
Mira Quill medical-note case records a durable, bearer-attributed inhaler outcome
after UPDATE, but reveals it only from the later attendance-note beat using the
bearer's then-current graph presentation. The credentials mechanic supplies the
case receipt; it does not decide the school meaning or change scoring.

The attendance note also prepares one authored return encounter. That encounter
uses a fresh packet with the same graph-owned bearer UUID and receives the first
case receipt as semantic prior context. Its recognition prose resolves the
bearer's current presence only when the return is entered.

## Playable-vertical acceptance

The playable invariant is that a player can understand a school-paperwork
decision without being told the evaluator's answer: inspect Mira Quill's note,
make a ruling from its visible missing signature, and later understand the
world-authored inhaler consequence and return encounter.

The worked vertical has parity at these surfaces:

- **Mechanical:** the credentials loop scores the ruling; the Hall Monitor
  authority records only an attributable receipt-derived consequence.
- **Narrative:** the attendance note exposes the later school-specific outcome,
  and the return resolves the current presentation of the same bearer.
- **Text/media floor:** packet and document prose remains sufficient when no
  generated card is available; media is additive rather than a prerequisite for
  deciding.
- **Visual witness:** the second fixed encounter presents Rowan Vale with red
  hair while the generated student-ID card depicts its distinct blond recorded
  subject. The ordinary subject-binding defect remains undisclosed until the
  player inspects or verifies the ID.
- **Playable client:** the reference web client renders packet pieces,
  inspection findings, and public action labels without receiving an expected
  disposition or hidden validity field.

### Repeatable local pass

Start the service and client in separate terminals. The client is a rendering
witness; create the local session through the documented REST API first.

```bash
poetry run tangl-serve
curl -X POST 'http://127.0.0.1:8000/api/v2/user/create?secret=dev-secret-123'
curl -X POST \
  'http://127.0.0.1:8000/api/v2/story/story/create?world_id=hall_monitor&init_mode=EAGER' \
  -H "X-API-Key: $(curl -s 'http://127.0.0.1:8000/api/v2/system/secret?secret=dev-secret-123' | jq -r .api_key)"
cd apps/web
VITE_DEFAULT_API_URL=http://127.0.0.1:8000/api/v2 \
VITE_DEFAULT_WORLD=hall_monitor \
VITE_DEFAULT_USER_SECRET=dev-secret-123 \
yarn dev
```

In the browser, first meet Tess Alder and inspect her incomplete medical waiver.
You may retain that visible document at the desk or settle her case normally.
Later, Mira Quill has no medical waiver: without the retained document, the
ordinary deny/compassionate branches remain available and no reissue action
appears. With the retained document, the authorized reissue completes the same
component and issues it into Mira's fresh packet; the ordinary credential
evaluator then derives `PASS`. A rules-correct `Send back to class` path still
reveals the inhaler outcome at the attendance note and offers `Meet the
returning student`. An incorrect compassionate `Allow onward` path produces the
contrasting world-authored outcome without changing the underlying score rule.
An arrest does not offer a return. The return is an ordinary new credential
encounter: its packet is fresh, while its bearer is the same live graph subject.

### Current framework friction

- The REST creation route is currently `/story/story/create`; the web client
  consumes an existing session rather than owning session/world selection.
- The web client gates API-backed components until authentication completes and
  disables prior transcript choices, so the current live frontier remains the
  only submit surface.
- Service world resolution reuses one compiled world per configured directory
  set. This prevents repeated service reads from recompiling the same singleton
  world during media and journal delivery.
