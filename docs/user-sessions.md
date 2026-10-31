# ARIA Home: 15-minute user-session kit

**Status: No user testing has been done yet.** The results table below is
empty on purpose. A row is filled only from a real session's notes.

Demo: https://aria-home-demo.onrender.com (synthetic data, no sign-in).
This is not a medical or emergency service and controls no equipment.

Drafted by Meta AI (web chat, 2026-10-30) from a brief written for this
project, and edited by Claude. The draft's example results row and its
example counts were removed so no invented result appears here.

## 1. Before the session

**Prepare:**
- The link, opened and tested: https://aria-home-demo.onrender.com
- A timer (phone timer set to 15 minutes)
- A note sheet for each person: Q1-Q5, plus space for confusion, approve/decline and a quote
- A pen, water and a quiet table

**Who:** 5 adults, one at a time. Family caregivers of an older parent, with
at least 1 person who knows residential HVAC (an installer, a technician or an
experienced homeowner).

**Consent script (read exactly):**
"May I take written notes and quote you without your name for this project?
You can stop at any time for any reason. We will not make any audio or video
recording without your clear permission."

Wait for a yes. If they say no to quoting, still take notes but mark them
"no quote consent".

## 2. Part A, baseline (2 minutes)

Show ONLY this text, on paper or a phone. Do not show ARIA yet:

> Thermostat offline. Last seen 1:30 AM.

Say: "This is how a normal thermostat app alerts you. What do you make of it?"

Ask Q1-Q5 and write down their exact words:

- Q1. Is something wrong, and what evidence supports that?
- Q2. What should you do next?
- Q3. What does approving HVAC contact authorize?
- Q4. Does the technician's report prove the home is warm?
- Q5. What does "goal verified" actually mean?

Score the baseline after they answer. Do not correct them.

## 3. Part B, ARIA Home (10 minutes)

Give them the link and say ONLY this:
"Please go through the warm-by story as if this were your mother's home.
Think aloud."

Do not explain, help or answer questions about the app. If they ask what to
do, say "Do what you would do at home."

The story is 10 steps about one winter night:
- The furnace stops and the thermostat goes silent.
- An independent room sensor shows 52 F and falling.
- ARIA says "may not be warm by 7:00" and asks "May I contact the HVAC
  company?" At the 02:31 step, let them choose Approve or Decline themselves.
- ARIA waits for independent readings and verifies that 68 F was held.
- It treats the technician's report as a report, not proof, and ends "warm by
  7:00".

When they finish, ask Q1-Q5 again, this time about ARIA, not the old alert.
Stop at 15 minutes even if they have not finished.

## 4. Scoring rubric

For each question, mark Correct (C), Partly (P) or Wrong (W).

- **Q1 Correct:** the room sensor reading 52 F and falling while the
  thermostat is silent shows the house is cooling.
- **Q2 Correct:** decide whether to let ARIA contact the HVAC company on file.
- **Q3 Correct:** only contacting the HVAC company on file, with the property,
  access note and observations, and nothing else.
- **Q4 Correct:** no. Only independent temperature readings verify warmth; the
  technician's report is just a report.
- **Q5 Correct:** independent room readings held 68 F for 30 minutes before
  7:00. It is not proof of what was repaired.

Partly means they get part of the answer but miss a key piece. Wrong means
the opposite answer, or no evidence.

## 5. Also record for each person

- **Completed the story without help:** yes or no. Yes means you did not
  explain anything or point at the screen.
- **Moment they were most confused:** in their own words.
- **Approve or Decline at 02:31, and why:** in their own words.
- **One sentence they would say about it to a friend:** quote it only if they
  consented.

## 6. Results table

Fill in one row per person, only from real session notes.

| participant | role | baseline Q1-Q5 | ARIA Q1-Q5 | completed unaided | main confusion | approve/decline + why | consented quote |
|---|---|---|---|---|---|---|---|
| P1 | | | | | | | |
| P2 | | | | | | | |
| P3 | | | | | | | |
| P4 | | | | | | | |
| P5 | | | | | | | |

Write scores like this: `Q1:C Q2:P Q3:W Q4:C Q5:C`.

## 7. After all five

1. Count each question out of 5, for the baseline and for ARIA separately
   (for example, "Baseline Q4 Correct: n/5. ARIA Q4 Correct: n/5").
2. Find the most common confusion: read all the "main confusion" notes and
   group the ones that say the same thing.
3. Pick ONE change that would fix that confusion.
4. Retest that one change with 1-2 new people, using the same 15-minute script.

Five sessions are early learning to improve the design. They are not proof
that the product works for everyone, and they are not market validation.
Write what you saw, not what you hoped.
