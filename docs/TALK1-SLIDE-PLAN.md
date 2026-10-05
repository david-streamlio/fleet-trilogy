# Talk 1 — "Edge Intelligence for Connected Fleets" — Slide Plan

Synced from the built deck (`Talk 1 Edge Intelligence.dc.html`) on 2026-09-30. The deck is the source of truth; this file mirrors its order, on-screen text and speaker notes.

40-minute slot, 26 slides: untimed Waitroom, Title and Thank You slides, and 23 narrative slides in five acts.

## Structure
1. **Problem** (slides 3–7): cloud observability bottleneck and the cost of edge hardware.
2. **Proposed Solution** (8–10): small LLMs on commodity, CPU-only hardware.
3. **Architecture** (11–13): Apache Pulsar Functions on the edge device.
4. **Use Case** (14–22): fleet context, the telemetry event, the co-processor gate, then the LLM gate that decides the cellular uplink, then the live demo.
5. **Conclusion** (23–25): feasibility validated, with the 1-bit caveat; teaser for Talk 2.

## Changes since the previous plan
- The BitNet journey (old slides 10–23: plan, fork, build bugs, "@@@@", ruling out causes, lessons, runbook) moved to Talk 2. See `TALK2-HANDOFF-FROM-TALK1.md`.
- "1-bit / small quantized LLMs" is now "small LLMs" throughout. Slide 24 notes that 1-bit models failed on the Pi due to software compatibility.
- The problem is framed as two parts (expensive edge hardware, slow cloud decisions), both addressed by the edge architecture.
- Now/Dream cost slides moved up into Act 1.
- New: Two Problems, Proposed Solution, Compute Spectrum, What Are Pulsar Functions, Embedded Architecture Blueprint, the co-processor sequence, co-processor payload, LLM enrichment card, LLM uplink sequence, Conclusion, Cliffhanger, and section dividers for each act.
- Gate order: the co-processor filters noise first, then the LLM decides what crosses the cellular link (high severity only).
- Sources moved into slide footers. Unsourced figures softened ("up to 90%/95%", "$100s").

## Open items
- Slide 22: record the demo. Broker placement and entry-point command are resolved (`./deploy/demo.sh pulsar://localhost:6650 --simulator-host <pi-hostname-or-ip>`, broker on the Pi — see `TODO-DEMO-RECORDING.md`); the recording itself is still outstanding.
- Slide 21's uplink gate is now implemented (`LlmTriageFunction.process()`, `uplink_min_severity`). See `TODO-TRIAGE-UPLINK-GATE.md`.
- Unsourced: "up to 95% noise / 90% bandwidth savings" (slides 4–5), the 97%+ figure (slide 7), "sub-millisecond" (slide 12).
- Time budget per slide not yet set.

---

### Slide 1 — Welcome! We'll begin shortly.
**Label:** Waitroom

**On-screen text:**
```
Edge Intelligence for Connected Fleets
Grab a coffee and settle in. While you wait, here are some interesting facts about Apache Pulsar
Apache Pulsar facts
```

**Speaker notes:** Lobby slide. Leave up while attendees join; the countdown and Pulsar facts run on their own.

### Slide 2 — Edge Intelligence for Connected Fleets: 1-Bit LLMs Inside Apache Pulsar Functions
**Label:** Title

**On-screen text:**
```
David Kjerrumgaard
Apache Pulsar Committer
```

**Speaker notes:** Untimed title slide. Introduce yourself, then go straight into the use case.

## Act 1 — The Problem

### Slide 3 — Two Problems with Today's Connected Solutions
**Label:** Two Problems, One Thesis

**On-screen text:**
```
01
The Cost Barrier
Edge intelligence today means dedicated, expensive in-vehicle compute.
02
Cloud Observability Bottlenecks
Every reading goes to the cloud, and every decision waits for the round trip.
Thesis
Smaller LLMs deployed on the edge can solve both problems.
To democratize edge safety, software must leverage pre-existing, low-cost commodity processors already on the road.
Edge Intelligence for Connected Fleets
03
```

**Speaker notes:** Today's connected fleet solutions have two problems. First, cost: the industry's answer to edge intelligence is dedicated, expensive compute in the vehicle. Second, the cloud observability bottleneck: without intelligence at the edge, every reading goes to the cloud, and every decision waits for a round trip. The thesis of this talk is that smaller LLMs deployed at the edge can solve both. To democratize edge safety, software must leverage the pre-existing, low-cost commodity processors already on the road.

### Slide 4 — Current Architecture: Cloud-Centric Observability Bottlenecks
**Label:** 04 Before: Cloud-Centric

**On-screen text:**
```
High Decision Latency (10s – Minutes): Critical safety events must make a full cloud round-trip before any action is taken.
Bandwidth Bleed: Massive cellular costs incurred by continuously transmitting normal, repetitive readings.
Network Dependencies: Total loss of visibility and real-time tracking when a vehicle enters a cellular dead zone.
Dumb Edge
raw, unfiltered
High-Latency Cellular Pipeline
RPM
GPS
Brake wear
Cloud Core
Overloaded
Ingestion Queues
Stream Processing
Lagging
Data Lakes
Up to 95% Noise Data
Decision Latency
BEFORE
10s – minutes
AFTER
Sub-second
Data Efficiency
Up to 95% noise data
Up to 90% bandwidth savings
Network Risk
Visibility lost in dead zones
Offline autonomy
Edge Intelligence for Connected Fleets
04
```

**Speaker notes:** This is how fleet observability works today without edge intelligence. Every truck is a dumb edge: it streams raw, unfiltered telemetry, RPM, GPS, brake wear, continuously, over a high-latency cellular pipeline into one cloud core. That core has to ingest, queue, process and store all of it, and most of it is normal, repetitive readings. Three costs follow. Decision latency: a critical safety event has to make a full cloud round-trip, tens of seconds to minutes, before anyone acts. Bandwidth bleed: you pay cellular costs to ship noise. And network dependency: when a truck drives into a dead zone, you lose it entirely. Next, the same fleet with the intelligence moved onto the truck.

### Slide 5 — Democratizing the Edge with Resource-Constrained Hardware
**Label:** 05 After: Edge Intelligence

**On-screen text:**
```
Algorithmic Efficiency over Raw Power: Utilizing highly optimized small LLMs to run complex diagnostic reasoning on sub-$100 commodity hardware. Source: Raspberry Pi 4 from $35 (raspberrypi.com); 2GB $55 (PiShop.us)
Localized Diagnostic Autonomy: The edge device acts as an intelligent gatekeeper, running real-time inference on vehicle telematics without a cloud connection.
Frictionless Fleet Scaling: Shifting to low-footprint hardware drives down hardware deployment costs compared to traditional AV computing platforms.
Commodity Edge Node (Raspberry Pi 4 Class Hardware / 4GB-8GB RAM)
Small LLM · Edge Diagnostics Model
Smart Edge
Sub-second Local Action
Filtered Anomalies Only (Up to 90% Bandwidth Savings)
Lean Cloud Core
Operations Control Center
Decision Latency
BEFORE
10s – minutes
AFTER
Sub-second
Data Efficiency
Up to 95% noise data
Up to 90% bandwidth savings
Network Risk
Visibility lost in dead zones
Offline autonomy
Edge Intelligence for Connected Fleets
05
```

**Speaker notes:** Now the same fleet with edge intelligence, and the point of this talk: it doesn't take a mobile supercomputer. Each truck gets a commodity edge node, Raspberry Pi 4 class hardware with 4 to 8 GB of RAM, running a small LLM as a lightweight diagnostics layer. The node acts as a gatekeeper: it runs inference on the truck's telematics locally, with no cloud connection required, and only filtered anomalies go over cellular. Massive compute is not what buys the bandwidth savings; putting judgment at the edge does. Whether it really performs on a Pi is the next question.

### Slide 6 — The 'Now' State: The High-Cost Barrier to Consumer Adoption*
**Label:** 25 Now: The Cost Barrier

**On-screen text:**
```
The Cost Bottleneck of Luxury Hardware
Prohibitive Unit Economics: Traditional edge intelligence requires dedicated silicon, adding thousands to bill-of-materials (BOM) costs.
Ecosystem Isolation: Features are tied to the vehicle's manufacturing lifecycle, becoming obsolete within a few years.
Luxury Gatekeeping: Advanced local diagnostics and safety features remain premium options, locked away from everyday drivers.
Spec
NVIDIA DRIVE Thor
Tesla HW4
AI inference
1,000–2,000 TOPS
~243 TOPS (2 chips)
CPU
14-core Arm Neoverse V3AE
20× Cortex-A72 per chip
Accelerator
Blackwell GPU + Tensor Cores
3 custom NPUs per chip
RAM
64–128GB LPDDR5X
16GB GDDR6
Power
~40–130W
~80–100W (est.)
Cost
$600–1,300 per chip (est.)
~$3,640 service unit
~$3,000+
per vehicle, high-end AV platform
Up to 130W
power draw, plus liquid cooling and wiring
Thousands
in added cost per vehicle
Edge Intelligence for Connected Fleets
*Thor: NVIDIA DRIVE AGX Thor developer docs (Dec 2025); chip price est. MarketResearch.com (2025). HW4: SemiAnalysis teardown (TOPS, memory); Electrek (2025, power est.); OEM service-unit listing (cost).
25
```

**Speaker notes:** Zoom out from fleets to consumer vehicles. Right now, if a car company wants to give a vehicle true local intelligence, it treats the car like a moving data center: dedicated automotive silicon like NVIDIA DRIVE Thor or Tesla's HW4 computer, thousands of dollars per vehicle, liquid cooling, and a large power budget. That keeps advanced local diagnostics and safety features locked in premium tiers. HW4 specs are from teardown analysis; Tesla does not publish them.

### Slide 7 — The 'Dream' State: Mass Democratization via Handheld Hardware
**Label:** 26 Dream: Democratization

**On-screen text:**
```
BYOD (Bring Your Own Device)
$0 Incremental Cost
Running optimized small LLMs directly on consumer mobile processors (e.g., standard smartphone NPUs). The phone interfaces with the car via Bluetooth or a cheap $15 OBD-II dongle. Source: ELM327 Bluetooth adapters, ~$5–30 retail
Impact: Instantly turns 1.4 billion existing consumer cars into "smart edge" vehicles overnight. Source: ~1.475B passenger cars in use, 2024 (WhichCar)
The Handheld Plug-and-Play Node
$100s Retail Cost
A tiny, low-power standalone dongle powered by ultra-affordable chips (like a Raspberry Pi Zero or Pi 4 equivalent footprint) that plugs straight into the dashboard.
Test bed (stand-in for a consumer device): Raspberry Pi 4 · 4-core Arm Cortex-A72 · 8GB RAM
Impact: Modest algorithmic efficiencies remove the need for fans, heavy wiring, or high battery drain.
By shifting intelligence from custom automotive silicon to small LLMs on handheld hardware, deployment cost drops by 97%+ while making edge safety accessible to 100% of drivers.
NEEDS: source
Edge Intelligence for Connected Fleets
26
```

**Speaker notes:** The dream of democratization happens when we stop trying to change the car's hardware and instead change the software's footprint. Optimize the model down far enough and the compute requirement shrinks to something already in every driver's pocket, their phone, or to a small plug-in dongle in the Pi class. That's how edge intelligence moves from a luxury option toward a universal safety standard. [NEEDS: source for the 97%+ figure before presenting.]

## Act 2 — The Proposed Solution

### Slide 8 — The Paradigm Shift & Compute Spectrum
**Label:** 06 Does It Work on a Pi?

**On-screen text:**
```
Edge Intelligence for Connected Fleets
06
```

**Speaker notes:** The obvious question after that promise: does any of this actually run on a Pi-class device? That answer, with real accuracy, latency and resource numbers from the Pi 4, is the subject of Talk 2, The Greenest Token. This talk stays on the problem and on how Pulsar Functions fit into the edge architecture.

### Slide 9 — The Proposed Solution – Small LLMs
**Label:** 09 Proposed Solution: Small LLMs

**On-screen text:**
```
Smaller LLMs deployed on the edge can solve both problems.
Algorithmic Efficiency: Shrinking model footprint rather than expanding hardware cost.
Bypassing Accelerators: Intentionally removing the GPU/NPU dependency to target ubiquitous silicon.
Traditional LLM
Small LLM
Model footprint
Large, full-precision weights
quantize
Small, dense weights
Required silicon
GPU / NPU accelerator
General-purpose CPU loop
Edge Intelligence for Connected Fleets
09
```

**Speaker notes:** The proposed solution flips the usual approach. Instead of adding hardware until a model fits, shrink the model until it fits the hardware that's already there. Small LLMs compress what a traditional model does that needs GPU or NPU acceleration into something small and dense enough to run in a pure CPU execution loop. Removing the accelerator dependency is deliberate: it's what lets the software target ubiquitous silicon.

### Slide 10 — Visualizing the Compute Spectrum*
**Label:** 10 Pure-CPU Compute Spectrum

**On-screen text:**
```
"If a small LLM reasons successfully on an unassisted Pi CPU, it can run effortlessly on consumer smartphones."
Edge Intelligence for Connected Fleets
*Sources: Apple A18 Pro Neural Engine, 35 TOPS (Apple); Pi 4 2GB, $55 (PiShop.us)
10
```

**Speaker notes:** Map compute architecture from left to right. Cloud cores have effectively unlimited GPU clusters. Luxury edge AV platforms bring 500-plus TOPS of dedicated NPU. Smartphones sit around 35 to 80 TOPS of NPU. At the far right is the commodity test-bed: a Raspberry Pi 4, a quad-core ARM CPU with zero AI TOPS. Traditionally, running an LLM was only feasible from the cloud to the luxury edge. The bet of this talk is that small LLM architectures extend feasibility all the way to the Pi, which stands in here for a consumer electronic device. And if a small LLM reasons successfully on an unassisted Pi CPU, it can run effortlessly on consumer smartphones. Sources: Apple A18 Pro 35 TOPS (Apple); Pi 4 2GB $55 (PiShop.us).

## Act 3 — The Solution Architecture

### Slide 11 — The Solution Architecture & Apache Pulsar
**Label:** Section: Solution Architecture

**On-screen text:**
```
Edge Intelligence for Connected Fleets
11
```

**Speaker notes:** Section divider. From the idea to the architecture: how Apache Pulsar Functions and small LLMs fit together on the edge.

### Slide 12 — What are Apache Pulsar Functions?
**Label:** 12 What Are Pulsar Functions?

**On-screen text:**
```
Zero-Infra Compute
Lambda-style serverless compute loops running directly inside the messaging broker layer.
broker
ƒ(x)
Native Stream Processing
Intercepts incoming telemetry topics, evaluates local state, and routes alerts instantly without external streaming engines.
topic
alert
Lightweight Footprint
Highly isolated, sub-millisecond execution thread tailored for resource-constrained embedded nodes.
one thread on an embedded node
Edge Intelligence for Connected Fleets
12
```

**Speaker notes:** A quick point of reference for anyone who hasn't used them. Pulsar Functions are lambda-style serverless compute that runs inside the messaging layer, so there's no separate compute infrastructure to stand up. They consume a topic, evaluate local state, and route results to another topic, which covers stream processing without an external streaming engine. And they're lightweight: an isolated execution thread small enough for resource-constrained embedded nodes. That last property is what makes them a fit for the truck. [NEEDS: source for the sub-millisecond figure.]

### Slide 13 — Embedded System Architecture Blueprint
**Label:** 13 Embedded Architecture Blueprint

**On-screen text:**
```
On the vehicle
Vehicle CAN Bus Sensors
raw readings
Local Pulsar Broker Ingestion Topic
telemetry in
Anomalous Event Filtering Logic
anomalies only
Pulsar Function: LLM CPU Runtime Engine
stays in local CPU memory
Cloud
Filtered Egress Pipeline to Cloud Control Center
Edge Intelligence for Connected Fleets
13
```

**Speaker notes:** Here's the blueprint on the vehicle. CAN bus sensor readings land on a local Pulsar ingestion topic, on a broker running on the edge device itself. Anomalous-event filtering logic runs first, so only filtered events reach the model; that keeps the LLM from building up a backlog. A Pulsar Function, running inside the local broker, hosts the small LLM on a CPU runtime and evaluates each filtered event. Its output goes out through the filtered egress pipeline to the cloud control center. The processing boundary, function plus model, stays entirely inside local CPU memory.

## Act 4 — The Connected Fleet Use Case

### Slide 14 — The Connected Fleet Use Case
**Label:** Section: Connected Fleet Use Case

**On-screen text:**
```
Edge Intelligence for Connected Fleets
14
```

**Speaker notes:** Section divider. From the architecture to the use case: what the connected fleet actually sends, and how the pipeline turns it into a decision.

### Slide 15 — Watching the Whole Fleet
**Label:** 01 Watching the Whole Fleet

**On-screen text:**
```
A control center observes every class 8 truck at once. When one truck slows down, that becomes a signal for the rest of the fleet to reroute.
01
```

**Speaker notes:** Start at the highest level: this talk is about observing an entire fleet of class 8 trucks, semi-trucks, not a single vehicle. A control center watches every truck at once, much like flight control or air traffic control. The point of watching is to catch a vehicle that is slowing down and use it as a signal to the rest of the fleet: reroute before they reach the same stretch of road.

### Slide 16 — Every Truck Reports In
**Label:** 02 Every Truck Reports In

**On-screen text:**
```
A small onboard computer collects sensor readings from across the rig and sends them back to the control center over cellular.
02
```

**Speaker notes:** Zoom in to one truck. Each rig carries a small onboard computer that collects readings from sensors across the tractor and sends them back to the control center over cellular. That onboard computer is where this talk's code runs.

### Slide 17 — What a Truck Senses: One Telemetry Event
**Label:** 03 What a Truck Sends

**On-screen text:**
```
{
"timestamp"
: "2026-10-14T14:32:05Z"
,
"truck_id"
: "truck-47"
"speed_mph"
: 33.8
"gps"
: { "lat"
: 33.9612
, "lon"
: -84.4000
"heading"
: 0.0
"route_segment"
: "I-95N-segment-4"
"corridor"
: "I-95N"
"planned_eta"
: "2026-10-14T15:05:00Z"
"current_eta"
: "2026-10-14T15:12:12Z"
"signals"
: {
"rolling_avg_speed"
: 36.1
"eta_slip_min"
: 7.2
"stop_go_index"
: 0.74
"brake_events"
: 1
"downshift_events"
"peak_deceleration_g"
: 0.31
"abs_engaged"
: false
> 2k
sensor readings per truck
Edge Intelligence for Connected Fleets
03
```

**Speaker notes:** This is what one of those readings looks like on the wire: a single TelemetryEvent, published to the truck-telemetry topic. Speed, GPS, heading, route segment and corridor, planned versus current ETA, cheap-math signals, and raw braking readings. Values shown are illustrative of a truck mid-slowdown. Each truck carries more than 2,500 sensor readings in total. Every schema and pipeline stage that follows exists to turn this stream into a reroute decision.

### Slide 18 — How a Slowdown Becomes High Severity
**Label:** Co-Processor Sequence

**On-screen text:**
```
One truck, five readings in a row: truck-47
on I-95N
Severity = ETA impact. How badly a slowdown threatens the delivery window, not a crash.
truck-47
rolling_avg_speed
stop_go_index
eta_slip_min
peak_decel_g
abs_engaged
Co-processor result
HIGH
truck-47, I-95N: ETA slipping 5.4 min and climbing, ABS engaged. Only events that clear the gate reach the LLM.
Edge Intelligence for Connected Fleets
18
```

**Speaker notes:** Before the payload, watch a sequence of readings from a single truck, truck-47, flow into the co-processor, 45 seconds of driving on I-95N. First, severity here is about delivery impact: how badly a slowdown threatens the ETA, not a crash. At zero seconds the truck is cruising; no signals fire and nothing is sent. At ten seconds average speed drops under 40, but low speed alone is noise. At twenty seconds stop-and-go kicks in and all three signals fire, but the ETA has only slipped 2.4 minutes, under the 3-minute gate, so it isn't worth LLM time. At thirty seconds the ETA slip crosses the gate: a real slowdown, and moderate braking with a stop-go index of 0.74 gives a medium baseline. At forty-five seconds ABS engages, which always forces high. That's the event the next slide shows as a triage payload. Values are illustrative; thresholds are the real ones from detection.py, coprocessor.py and severity_classifier.py.

### Slide 19 — What the Co-Processor Sends: One Triage Payload
**Label:** What the Co-Processor Sends

**On-screen text:**
```
{
"truck_id"
: "truck-47"
,
"corridor"
: "I-95N"
"signals"
: [ "sustained_low_speed"
, "stop_go_index"
, "eta_slip"
],
"metrics"
: {
"rolling_avg_speed"
: 36.1
"eta_slip_min"
: 7.2
"traffic_pattern"
: "elevated velocity variance (frequent speed cycling)"
"peak_deceleration_g"
: 0.31
"abs_engaged"
: false
"baseline_severity"
: "medium"
"contextual_triggers"
"local_time"
: "2026-10-14T14:32:05+00:00"
"weather_condition"
: "Heavy rain, wet asphalt"
"cargo_type"
: "Liquids / Chemical Tanker"
"dispatch_status"
: "Running 20 minutes behind schedule"
medium
baseline severity
set before the LLM runs; the LLM only raises, holds, or lowers it
Edge Intelligence for Connected Fleets
19
```

**Speaker notes:** Here's what comes out of the co-processor. The raw reading has passed the cheap-math slowdown check and the ETA-slip magnitude gate, so it's worth the LLM's time. The payload names which signals fired, restates the metrics, turns the stop-go index into a plain-language traffic pattern, and adds context a threshold can't capture: weather, cargo, dispatch status. It also carries a baseline severity, computed deterministically before the LLM runs. The LLM's only job is to raise, hold, or lower that baseline. Payload shape per coprocessor.build_triage_payload; values follow the telemetry example on the previous slide.

### Slide 20 — What the LLM Decides: One Enrichment Card
**Label:** What the LLM Decides

**On-screen text:**
```
{
"risk_synthesis"
:
"Heavy rain degrades traction, the cargo is a
liquid chemical tanker, and the driver is 20
minutes behind under schedule pressure. All
three are risk multipliers."
,
"escalation"
: "raise"
, // LLM decision
"truck_id"
: "truck-47"
"baseline_severity"
: "medium"
, // from co-processor
"severity"
: "high"
, // medium + raise
"recommended_action"
: "Escalate for driver/dispatcher review."
"eta_impact"
: 7.2
// minutes
medium →
high
the LLM raised it
final severity high, so this card goes over cellular to the control center
Edge Intelligence for Connected Fleets
20
```

**Speaker notes:** This is what comes out of the LLM for the payload on the previous slide. The model only writes two things: a risk_synthesis explaining its reasoning, and an escalation of raise, hold, or lower. Here it reads heavy rain, a liquid chemical tanker, and a driver running behind, and raises. Everything else on the card is deterministic: the final severity is the baseline moved one step, medium to high; the recommended action is a lookup on the escalation; eta_impact is the measured slip in minutes. Because the final severity is high, this card is what goes over the cellular link. Card shape per LlmTriageFunction.process; the risk_synthesis text is illustrative.

### Slide 21 — The LLM Decides What Crosses the Cellular Link
**Label:** LLM Uplink Sequence

**On-screen text:**
```
Uplink rule: only cards with a final severity of high go over cellular to the control center. Everything else is logged on the truck.
truck · time
baseline
weather_condition
cargo_type
dispatch_status
LLM
severity
Uplink
2 of 5
triaged events cross the cellular link; raw readings never do. The cloud observability bottleneck, relieved at the source.
Edge Intelligence for Connected Fleets
21
```

**Speaker notes:** Now watch several gated payloads reach the LLM on the edge device, across the fleet. The co-processor decided what the LLM sees; the LLM decides what leaves the truck. The rule: a card goes over the cellular link to the control center only if its final severity is high. Truck-47 at 30 seconds: medium baseline, but rain, a chemical tanker and schedule pressure, so the LLM raises it to high and it's sent. Truck-12: medium, but clear, dry, general freight and on schedule, so it's lowered and stays on the truck. Truck-31: low and nothing to move it, so it holds and stays. Truck-08: a physics-high, but the dispatch status says the driver completed an evasive maneuver, so the LLM lowers it and it stays local. Truck-47 again at 45 seconds with ABS: high, raised, clamped at high, sent. Two of five triaged events cross the cellular link, and every raw reading before them never did. That is the cloud observability bottleneck relieved at the source. This is exactly what `LlmTriageFunction.process()` does today — it calls `build_card()`, then gates on `uplink_min_severity` (default `high`): anything below that threshold publishes straight to the local-only topic instead of `enrichment-cards`. Other trucks' contexts are illustrative.

### Slide 22 — See It Running, End-to-End
**Label:** 24 See It Running

**On-screen text:**
```
Demo recording
Pi console running deploy/demo.sh · fleet-simulator
publishing from the laptop · uplinked vs. local-only
cards live on the Pi console
Entry point · broker on the Pi
./deploy/demo.sh pulsar://localhost:6650 --simulator-host <pi-hostname-or-ip>
NEEDS: the demo recording. No source provides it yet.
Edge Intelligence for Connected Fleets
24
```

**Speaker notes:** Everything up to now has been a number on a slide — this is the actual Pi, running the actual co-processor and LLM triage functions via `deploy/demo.sh`, against actual telemetry, producing actual enrichment cards split live between what crosses the cellular link and what stays local. [NEEDS: the recording itself. The broker runs on the Pi for this take.] From here, the last slide zooms out past this one truck.

## Act 5 — Conclusions

### Slide 23 — Conclusions & Next Steps
**Label:** Section: Conclusions

**On-screen text:**
```
Edge Intelligence for Connected Fleets
23
```

**Speaker notes:** Section divider. Wrap up: what this showed, and what comes next.

### Slide 24 — Conclusion – Feasibility Validated
**Label:** Conclusion: Feasibility Validated

**On-screen text:**
```
Architecture Proven
Confirming small LLMs can run logic loops natively on general-purpose CPUs.
Bandwidth Slashed
Two gates, the co-processor then the LLM, drop most ambient sensor readings at the vehicle boundary before anything uses the cellular link.
Inferred from the gate design; not yet measured.
Democratic Blueprint
Unlocking real-time vehicle diagnostics on consumer smartphones and handheld plug-and-play modules.
Caveat: 1-bit LLMs specifically didn't work. Software compatibility issues blocked them on the Pi, so we substituted small quantized models that run on mainline llama.cpp.
Edge Intelligence for Connected Fleets
24
```

**Speaker notes:** Three things this project validated, with one caveat up front: the 1-bit LLMs in the original talk abstract did not work, because of software compatibility issues on the Pi, so we substituted small quantized models that run on mainline llama.cpp. The architecture works: small LLMs run their logic loops natively on general-purpose CPUs, inside Pulsar Functions on the edge. Bandwidth drops sharply because normal, steady-state telemetry never leaves the vehicle; only high-severity cards cross the cellular link. And that makes a democratic blueprint: the same approach points to real-time vehicle diagnostics on consumer smartphones and handheld plug-and-play modules. The bandwidth reduction is inferred from the double filtering, co-processor then LLM, not measured; say so if asked for a number.

### Slide 25 — But... How Well Did It Actually Perform?
**Label:** Cliffhanger: Talk 2

**On-screen text:**
```
Token Latency?
What happens when a commodity CPU handles massive sensor spikes?
Quantization Loss?
Did extreme quantization degrade our diagnostic accuracy?
ARM Compile Hurdles?
What engineering steps were required to run the stack on an ARM Cortex-A72?
Energy Efficiency?
How much power does each edge decision cost on a CPU-only node, compared to a GPU?
Part 2
Find out in Part 2: The Greenest Token Is the One That Never Hits a GPU.
Edge Intelligence for Connected Fleets
25
```

**Speaker notes:** It works. But that raises the obvious question: how well did it actually perform? Three things I haven't shown you. Token latency, and what happens when a commodity CPU handles massive sensor spikes. Quantization loss, and whether extreme compression hurt diagnostic accuracy. And the ARM compile hurdles, the engineering it took to get the stack running on a Cortex-A72. And energy efficiency: what each decision costs in watts on a CPU-only node compared to a GPU. All of that is Part 2.

### Slide 26 — Thank you
**Label:** 27 Thank You

**On-screen text:**
```
David Kjerrumgaard
Apache Pulsar Committer
```

**Speaker notes:** Transition to Q&A.
