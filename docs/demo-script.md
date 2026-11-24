# Retriever demo scripts

Max length 3:00. Record at 1280×800, light theme. The opening story is Mei Ling, a tuition-centre owner. She is illustrative, not a customer. Numbers on the Overview cards are labelled Simulated. Rescue rows and the audit feed are from this machine’s sandbox run.

Submission line, if you send the file: subject `Build Night Demo: Retriever by Timothy Lee`.

## Take A. Voiceover with the recorded walkthrough

The screen recording is `demo/retriever-demo.webm`. Read this while it plays. Do not add claims the screen does not show.

| Time | On screen | Say |
|---|---|---|
| 0:00–0:18 | Landing hero | Mei Ling runs a tuition centre. Parents pay by card or PayNow. By the fifth of the month some cards have failed, and the bank shows transfers with no invoice number. Retriever does that Sunday for her. |
| 0:18–0:32 | Problem figures | Late payment is common for Singapore SMEs. These three figures are from Xero and Atradius, 2025. Mei Ling’s paragraph is an illustration. |
| 0:32–0:55 | How it works, then Open the demo | Four jobs. Collect the invoice with its reference. Rescue a failed card onto PayNow. Match a transfer that arrived with no reference, and ask her only when the match is uncertain. Warn her before cash runs short. |
| 0:55–1:25 | Overview, approval card | This is the only thing that needs a yes. An S$800 transfer from TAN AH KOW TRADING. The suggestion names INV-104, gives the reason in a sentence, and says it came from the payer name and the amount. She approves. She does not retype a spreadsheet. |
| 1:25–1:55 | Forecast card and metric strip | The forecast is arithmetic, not a model. It names the lowest balance and offers a discount only when the discount costs less than the gap. Recovered, still at risk, and the rates sit under the queue. |
| 1:55–2:25 | Rescues | A Stripe test card, 4000 0000 0000 0002, declines. Retriever opens a rescue and drafts a PayNow message for the invoice. In the sandbox that link is a real HitPay checkout. Paying it shows Payment Completed for SGD 420.00. The rescue stays offered until the signed webhook arrives. |
| 2:25–2:50 | Audit | Every decline and every PayNow link is a line in the log: who did it, and why, in plain English. Nothing here is edited after the fact. |
| 2:50–3:00 | Hold on the audit | The agent creates links. It does not move money. Refunds wait for her approval. Card numbers stay with Stripe and HitPay. |

## Take B. Fallback, if a provider is down

Same timing. Skip the sentence about the live HitPay checkout. Say: “The rescue message is on screen. The PayNow link is created when the sandbox is up. The audit still shows each decline.”

## What this cut does not include

Live HitPay MCP balances, the EarlyBird discount sent to a parent, and Stripe Custom Payment Methods. The card-to-PayNow path does not need `cpmt_` ids. A completed PayNow page is not a paid invoice until `Hitpay-Signature` matches the endpoint salt.
