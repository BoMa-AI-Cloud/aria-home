Operator's note: README opening for judges; used after removing an entity tag.

--- Meta AI reply (verbatim) ---
# ARIA Home
Will an older adult's home be warm by morning, and if something looks wrong overnight, who should respond?

Demo: https://aria-home-demo.onrender.com (synthetic data, no sign-in)
Video: <video link>

I live in Petoskey, Michigan, where the winters are long and cold. As my in-laws get older, I've started wondering what happens when they can't fix something, or can't tell that something is wrong, and nobody is around to help. As an electrician, I've worked on houses with major damage from a fault that nobody caught in time. ARIA Home is built to notice sooner and get the right person moving. It does not repair or control anything, and it is not a medical or emergency service.

It is a solo entry in the 【entity-Meta¦canonical_name=Meta】 Global AI Developer Hackathon (Indie Developer track, theme "Build for Your World").

## What judges should click
1. Open the demo and press Start the warm-by story.
2. Step through the 10 steps with Next. The House tab shows the verdict, the house right now, and who knows.
3. At 2:31, press Approve or Decline on the caregiver permission request. Decline means no HVAC request and ARIA keeps monitoring.
4. Open Reasoning to see ARIA's view: sources, code checks, where the model contributes, the recorded muse-spark-1.3 answer and its muse-wonder-1.0 second review.
5. Open Integrations for what ARIA connects to and which Meta model does what: muse-spark-1.3, muse-wonder-1.0, sam-3.1, muse-voice-transcribe-1.0, muse-image-1.0.
6. Reset my session clears only your own session.

To run it locally, see Try it in 5 minutes below.

What it is: ARIA Home answers whether the home will be warm by the warm-by time and who should respond if something looks wrong overnight. Code decides readiness, verification, and who is told; muse-spark-1.3 explains under a contract and muse-wonder-1.0 reviews, sam-3.1 segments synthetic frames, muse-voice-transcribe-1.0 transcribes the synthetic voice note, muse-image-1.0 generated frames offline — models never decide. Notifications are scoped and simulated with allowed fields only, and verification uses later independent readings for temperature-goal verification, not proof of a repair. It does not repair or control anything and is not a medical or emergency service.