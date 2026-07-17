# Credential Gate

`credential_gate` is the checkpoint skin for the reusable credentials mechanic.
The live demo defines its restriction map and roster in `credential_gate/domain.py`,
and compiles its credential definitions from `credential_types.reference.yaml` through
the generic `assets` manifest declaration.

`credential_types.reference.yaml` is live loader input for the world-qualified
`CredentialDefinition` catalog. The shared compiler/loader contract is
`engine/src/tangl/mechanics/credentials/PHASE_6C_AUTHORED_CATALOG_HANDOFF.md`.

## Semantic operations versus skin vocabulary

The checkpoint and hall-monitor skins use the same normalized operations but
realize them differently:

| Semantic coordinate | Checkpoint syntax | Hall-monitor syntax |
| --- | --- | --- |
| origin | local / foreign region | upper / lower / exchange program |
| intention | travel / work / emigrate | academic / activity / off-campus |
| controlled item | weapon / drugs / secrets | uniform / medicine / records |
| identity | passport or state id | student id |
| authorization | visa, permit, waiver | hall pass, activity pass, doctor's note |
| inspect possessions | search baggage | search bag or locker |
| allow | admit traveler | allow student onward |
| deny | turn traveler back | send student back |
| arrest | detain traveler | send student to the office |

The mechanic owns packet discovery, restriction matching, inspection,
mediation, and disposition. The world owns indication identifiers, catalog
names, visible descriptions, rule language, narrative consequences, and
StoryTanglish projection. Thus a medical item may be narcotics at a checkpoint
and an inhaler in a hallway while both use the same controlled-item
authorization operation underneath.
