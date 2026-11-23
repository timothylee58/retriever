import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const body = (await request.json()) as { password?: string };
  const expected = process.env.DEMO_PASSWORD ?? "retriever-demo";
  if (body.password !== expected) {
    return NextResponse.json({ ok: false }, { status: 401 });
  }
  const response = NextResponse.json({ ok: true });
  response.cookies.set("retriever_demo", expected, { httpOnly: true, sameSite: "lax", path: "/" });
  return response;
}
