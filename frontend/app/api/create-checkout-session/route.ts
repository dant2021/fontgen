// pages/api/create-checkout-session.ts
import { NextResponse } from "next/server";
import Stripe from "stripe";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(req: Request) {
  try {
    const { jobId, returnUrl } = await req.json();

    const session = await stripe.checkout.sessions.create({
      payment_method_types: ["card"],
      line_items: [
        {
          price_data: {
            currency: "usd",
            product_data: {
              name: "Premium Font Package",
              description: `Font Job ID: ${jobId}`,
            },
            unit_amount: 2500, // $25.00 in cents
          },
          quantity: 1,
        },
      ],
      mode: "payment",
      success_url: `${returnUrl}&checkout=success&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${returnUrl}&checkout=cancel`,
      metadata: { jobId },
    });

    return NextResponse.json({ sessionId: session.id });
  } catch (err) {
    console.error("Stripe session creation failed", err);
    return NextResponse.json({ error: "Stripe session creation failed" }, { status: 500 });
  }
}