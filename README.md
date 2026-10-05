# agent-golden-set-eval

A minimal, runnable version of the evaluation method I use before releasing a
conversational agent that quotes prices: a golden set of scripted conversations,
deterministic checks against the expected outcome, and a release gate that fails
if a single quote is wrong.

The domain is a fictitious container rental company, Andes Box Rentals, in
Santiago, Chile. All customers, prices and conversations are invented. The
conversations are in Spanish because that is the language the agent serves; the
code and documentation are in English.

## The approach

1. **Write the scenarios before the agent.** Each scenario is a short
   conversation plus the outcome the business expects: the exact total the
   customer must hear, whether the case must go to a human, and which rules the
   agent must respect. Expected totals are calculated by hand and the arithmetic
   is written next to them, so a reviewer can audit the golden set without
   running code.
2. **Check outcomes deterministically.** A quote is either the right number or it
   is not. No model grades another model here. Every check is a plain function of
   the transcript and of the tool calls the runner recorded.
3. **Record what the agent did, not what it says it did.** The runner owns the
   toolbox the agent calls, so the checks see every CRM lookup, quote and handoff
   as it happened.
4. **Block the release on any failure.** The CLI exits non-zero if one scenario
   fails, and CI runs the golden set on every push. A wrong quote is a commercial
   commitment, so there is no pass threshold below 100%.

## What is checked

| Check | Fails when |
|---|---|
| `quote_total` | The last quote tool result differs from the expected total, or the agent never states that total to the customer. |
| `handoff` | The agent hands off when it should not, does not when it should, or gives the wrong reason. |
| `amounts_grounded` | The agent says a peso amount that no tool returned. |
| `customer_lookup_first` | The first tool call is not the CRM lookup. |
| `no_quote_after_handoff` | The agent keeps quoting after a human owns the case. |
| `quote_args_from_user` | The distance passed to the quote tool was never said by the customer. |
| `minimum_term_disclosed` | The minimum rental term changed the price and the agent did not say so. |

The first five rows apply to every scenario; the last two are opted into per
scenario.

## Layout

```
scenarios/                 13 golden-set conversations (YAML)
src/golden_eval/
  domain/                  fictitious catalog, freight table, CRM and pricing logic
  toolbox.py               tools the agent can call; every call is recorded
  agents/base.py           the Agent interface
  agents/reference.py      deterministic reference agent (no LLM, no API key)
  agents/broken.py         same agent with a realistic defect, to show the gate
  checks.py                outcome checks and rules
  runner.py, report.py     execution and pass/fail report
  cli.py                   golden-eval run
tests/                     unit tests for pricing and checks, plus the gate itself
```

A scenario looks like this:

```yaml
id: office-minimum-term
description: Office container requested for less than its 3-month minimum
caller_phone: "+56900000103"
turns:
  - Necesito un contenedor oficina por un mes.
  - Es para un evento a 10 km.
expected:
  # billed 3 months (minimum): 210.000 x 3 = 630.000; freight 60.000 x 2 = 120.000
  # net 750.000; VAT 142.500
  quote_total: 892500
  handoff: false
  rules: [minimum_term_disclosed, quote_args_from_user]
```

## Running it

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/pjcastillog95/agent-golden-set-eval.git
cd agent-golden-set-eval
uv sync
uv run golden-eval run                  # reference agent: 13/13, exit code 0
uv run golden-eval run --agent broken   # defective agent: release blocked, exit code 1
uv run pytest
```

Useful flags: `-v` prints every transcript, `--json reports/golden-set.json`
writes a machine-readable report.

The defective agent calls the quote tool but restates the total from its own
arithmetic and forgets the freight, which is the kind of mistake a language model
makes when it is allowed to do the math:

```
FAIL  basic-dry20               Known customer, one 20 ft container, short distance
      - quote_total: agent never stated the tool total
      - amounts_grounded: ungrounded amounts: [226100]
       user: Hola, necesito arrendar un contenedor de 20 pies por 2 meses.
      agent: Hola, Constructora Los Aromos. ¿A cuántos kilómetros de Santiago queda la obra o bodega?
       user: La obra está en Colina, a 15 km.
      agent: El total con IVA queda en $226.100.
...
4/13 scenarios passed
RELEASE: blocked
```

## Evaluating your own agent

Implement the interface in `agents/base.py` and pass a factory to the CLI:

```python
class MyAgent:
    def __init__(self, context: CallContext) -> None: ...
    def respond(self, history: Sequence[Message], tools: ToolBox) -> str: ...


def create(context: CallContext) -> MyAgent:
    return MyAgent(context)
```

```bash
uv run golden-eval run --agent my_package.my_module:create
```

An LLM-backed agent maps the `ToolBox` methods to its tool definitions and
returns the model's final text for the turn. Because model output varies between
runs, run the golden set several times for an LLM agent and require every run to
pass.

## Limits

- The reference agent extracts slots with keyword matching. It exists so the
  pipeline runs in CI without credentials, not as an example of language
  understanding.
- Deterministic checks cover what has a correct answer: amounts, routing and
  hard rules. Tone and helpfulness need a different review, and they should not
  gate a release on their own.

## License

MIT
