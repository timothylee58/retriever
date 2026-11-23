export function ApprovalCard() {
  return (
    <article className="approval">
      <header>
        <span className="kind">Match suggestion · AI</span>
        <span className="badge">New</span>
      </header>
      <p className="amount money">S$800.00 <span style={{ fontWeight: 400, fontSize: 14 }}>from TAN AH KOW TRADING</span></p>
      <p>INV-104 · Tan Trading Pte Ltd · <span className="money">S$800.00</span></p>
      <p className="reason">82% sure: the amount matches exactly, the payer name matches a known alias, and the invoice was due 3 days ago.</p>
      <p className="prov">HitPay · bank transfer · 14:02</p>
      <div className="btn-row">
        <a className="btn btn-primary" href="/queue">Approve</a>
        <a className="btn btn-ghost" href="/queue">Pick another invoice</a>
        <a className="btn btn-ghost" href="/queue">Reject</a>
      </div>
    </article>
  );
}
