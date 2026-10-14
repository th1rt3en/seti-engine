# @seti/protocol

The wire protocol between the engine service and its clients (the Durable Object, tests, tools).

- `schema/protocol.schema.json` is generated from the engine's pydantic models by `tools/engine/gen_protocol.py`.
- `src/types.ts` is generated from the schema by `pnpm --filter @seti/protocol generate` (json-schema-to-typescript).
- Neither file is edited by hand. A test in `services/engine/tests/test_service.py` fails when the schema is out of date.
- The protocol version is `PROTOCOL_VERSION` in `services/engine/src/seti_engine/protocol.py`.

## The service

`POST /new` `{options}` -> `{state, events, legal}`; `POST /apply` `{state, action}` -> `{state, events, legal}` (422 `{error, message, legal}` for an illegal action);
`POST /legal` `{state}`; `POST /project` `{state, viewer}` -> the view one player may see (hidden hands, decks and so on are blanked);
`GET /schema`; `GET /health`. Actions are opaque objects: send back one of the `legal` moves unchanged.
The service keeps no state: every request carries the whole game state. Never send a client the raw state, only `/project` output.
