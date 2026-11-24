const PORT = 8000;
const INACTIVITY_TIMEOUT_MS = 10 * 60 * 1000;

export interface Env {
  RETRIEVER_API: DurableObjectNamespace;
  DATABASE_URL: string;
  WEB_ORIGIN: string;
  DRY_RUN: string;
}

export class RetrieverApi extends DurableObject<Env> {
  private starting: Promise<void> | undefined;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
  }

  async fetch(request: Request): Promise<Response> {
    this.starting ??= this.startAndWait().finally(() => {
      this.starting = undefined;
    });
    await this.starting;
    const url = new URL(request.url);
    url.protocol = "http:";
    url.host = "container";
    const forwarded = new Request(url, request);
    forwarded.headers.delete("host");
    return this.ctx.container!.getTcpPort(PORT).fetch(forwarded);
  }

  private async startAndWait(): Promise<void> {
    const container = this.ctx.container!;
    if (!container.running) {
      container.start({
        image: container.images.base,
        instance: "basic",
        enableInternet: true,
        env: {
          DATABASE_URL: this.env.DATABASE_URL,
          WEB_ORIGIN: this.env.WEB_ORIGIN || "*",
          DRY_RUN: this.env.DRY_RUN || "true",
          HITPAY_ENV: "sandbox",
          HITPAY_API_BASE: "https://api.sandbox.hit-pay.com",
        },
      });
    }
    await container.setInactivityTimeout(INACTIVITY_TIMEOUT_MS);
    const port = container.getTcpPort(PORT);
    for (let attempt = 0; attempt < 100; attempt++) {
      try {
        const response = await port.fetch("http://container/health", {
          signal: AbortSignal.timeout(2000),
        });
        await response.body?.cancel();
        if (response.ok) return;
      } catch {
        // The server is still starting.
      }
      await scheduler.wait(300);
    }
    throw new Error("Retriever API did not become ready");
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const stub = env.RETRIEVER_API.getByName("api");
    return stub.fetch(request);
  },
};
