# verify.config.json details

Read this when the config needs an `env` map, a free port, or throwaway credentials.

## Keys

`baseUrl`, `startCommand`, `loginEnv`, and an optional `env`. The file holds names and
placeholders only, never a value.

## env map

`env` maps an app variable to a `$VERIFY_*` name, for example
`{"APP_USER": "$VERIFY_USER", "APP_PASSWORD": "$VERIFY_PASSWORD"}`. Each value must match
`^\$VERIFY_[A-Z_]+$`. Before it runs `startCommand`, the stage exports each app variable with the
value of the `VERIFY_*` variable it names.

## Free port

Pick a free port in your shell, for example
`PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')`,
then `export PORT`. The config writes `baseUrl` with a `${PORT}` placeholder, such as
`http://127.0.0.1:${PORT}`, and `startCommand` reads `PORT`. Substitute the value into `baseUrl`
before you use it.

## Throwaway credentials

Create them in your own shell, for example `export VERIFY_PASSWORD=$(openssl rand -hex 16)`, only when:

- `VERIFY_USER` and `VERIFY_PASSWORD` are unset;
- the stage starts the server itself with `startCommand`;
- the `Verify:` row or a Confirmed decisions comment says `throwaway credentials OK`.

Otherwise report BLOCKED. The password is random, lives for one run, and protects a server on
throwaway data that the stage started and stops. Never write it to a file, the PR or the config.
No code enforces the consent (`ship.js` is untouched): the rule is yours to keep.

Typing it with `browser_fill_form` is accepted for this case only. Never pass it through
`browser_run_code_unsafe`. Real or staging accounts keep owner-supplied variables: never invent them.
