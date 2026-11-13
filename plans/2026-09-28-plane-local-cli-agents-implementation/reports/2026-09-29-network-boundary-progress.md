# Network boundary progress

## Status

Story 3.4 remains in progress.
The Code MCP route supports separately approved exact literal-IP TCP destinations through the bounded command executor.
Commands without network authority retain the existing network isolation.
Hostname delivery remains pending the DNS product decision.

## Boundary and evidence

The trusted control container installs one atomic nftables transaction in its own network namespace.
The Agent container shares that namespace, runs as a non-root user, and has no capabilities.
The filter accepts exact resolved IP addresses and TCP ports and drops other traffic.
The filter supports IPv4 and IPv6.
IPv6 neighbour discovery has separate rules with a hop limit of 255.
Established replies and related ICMP errors can enter the namespace.
A second installation fails instead of adding a wider scope.
The approach uses Docker's documented [container network namespace](https://docs.docker.com/engine/network/) and [capability controls](https://docs.docker.com/engine/containers/run/).
The IPv6 control rules follow the [nftables neighbour discovery guidance](https://wiki.nftables.org/wiki-nftables/index.php/Simple_ruleset_for_a_workstation).

The native Docker check first proves that both peer containers serve TCP on ports 8080 and 8081 and UDP on port 8080 through both address families.
After filter installation, the Agent reaches the approved peer and namespace-local loopback endpoints through both address families.
Six unapproved TCP endpoint combinations and four UDP endpoints are blocked.
The Agent has zero effective capabilities and cannot change nftables.
The control container cannot install a changed scope in the same namespace.
The initial IPv6 probe failed because neighbour discovery was blocked.
The corrected filter passes the IPv6 probe.
The UDP probe was corrected to accept the kernel's immediate permission error as a blocked operation, as well as a receive timeout.

The loopback probe then reproduced a second failure: the request was allowed but the local server's reply was blocked at output.
The output rule now accepts only established packets in the reply direction, which preserves destination checks for original requests.
Validation: three network tests passed in 3.279 seconds with image `sha256:64ba2447abbd08ef92d63fce221284e82a510448892b413549e0c6ea4814e2ed`.
Ruff lint and format checks passed for the changed Python files.
The test removed its containers and network.

## Pinned permission scope

Plane now accepts a bounded `resolved_ips` snapshot on each network destination.
It normalizes and hashes these addresses with the host and port.
Run grant matching permits an IP subset but rejects new addresses, changed hosts, and changed ports.
Legacy grants cannot authorize pinned requests, and pinned grants cannot authorize legacy requests.
Requests cannot mix the two formats.
The API validates literal-host consistency and rejects invalid, interface-scoped, or unbounded address data.
Five focused contract tests passed in 1.78 seconds, including real API decisions and consumption under a Code reservation.
The complete permission contract file passed all 77 tests in 27.23 seconds.
The permission scope formatter now includes pinned IP addresses and brackets IPv6 literal hosts.
It falls back to the complete JSON for malformed IP lists instead of hiding those values.
All eight web helper tests, web type generation and TypeScript checks, focused OxLint, and formatting checks passed.
The type generation command still reports the existing Vite paths plugin notice and PostCSS module-type warning.
This turn did not perform a browser layout check for the new scope text.
These tests prove that a same-scope subset inherits an approved Run grant and that a changed IP or legacy grant leaves the request pending and consumption blocked.
Network execution and its durable lifecycle are still required in the Worker.

## Command-bound permission and resolution

The Worker now resolves exact TCP hosts through the system resolver in a separate process with a ten-second deadline.
It validates and retains the bounded IP snapshot for the later proposal; no DNS resolution occurs during grant matching.
The proposal builder binds that scope to one separately approved unused command request.
Plane validates the exact command, referenced permission, current Run identity, turn, lease, Worktree, and approving member.
Network consumption requires prior process consumption and rejects command completion, prior reconciliation, or a previously consumed network permission for that command.
The API continues to check pending Stop and the current Code reservation.
Four focused API cases passed in 2.42 seconds for matching authority, revoked membership, completed command, and Stop.
The full permission file passed all 82 tests in 28.95 seconds.
The Worker gate ran 27 tests in 9.636 seconds: 25 passed and two native Claude push/PR probes were explicitly skipped because their model opt-in was not set.
The new resolver checks use real system resolution for localhost and a literal IPv6 address.
Both API and Worker verify the same canonical network effect hash.
An initial Worker test used the macOS `/tmp` alias, which the existing exact-Worktree validator correctly rejected; the fixture now uses its canonical `/private/tmp` path.
The first API fixture attempt used stale event sequencing and incorrect Stop model fields; the corrected check posts command completion through the real Worker API and uses the existing Stop fields.
Ruff lint and formatting checks passed for the affected Python files.
The execution route remains disabled until namespace identity, durable preparation, result acknowledgement, Stop, and restart recovery are implemented.

## Durable network resources

The command journal now retains both permission identities, the exact network hash and scope, and a deterministic private resource manifest before Docker creation.
The manifest contains full Run, slot, and network permission identities, the pinned controller image, bridge and controller names, IPv6 subnet, and filter hash.
The journal persists `starting` before creation and `configured` only after verified filter installation and current-authority callback checks.
Cleanup records `removed` while retaining command evidence.
Invalid phase transitions, changed scope or resource data, and replay after configuration or removal are rejected.
Native child processes that exit before and after command result persistence retain the matching network facts.
Generic reconciliation and clearance cannot discard a network command record.

The internal Docker controller now creates and inspects the recorded bridge and root control container, checks fixed resource and security limits, installs the exact immutable filter, and removes only verified resources after the command container stops.
The controller has one added network administration capability and no Host mount or device.
The test Agent has zero effective capabilities.
The private controller adds a fixed 128 MiB memory bound per network operation.
The actual engine normalizes `NET_ADMIN` to `CAP_NET_ADMIN` and inserts the IPv4-enabled bridge option; verification accepts only these equivalent explicit values.
An initial subnet formatter was rejected by Python's IPv6 parser; subnet construction now uses the standard integer-address constructor and passes native bridge creation.
The native lifecycle check uses controlled authority callbacks and real Docker resources, not the paired Plane grant path.
It verifies denied authority before creation, journal presence at both authority checks, permitted IPv4 and IPv6 loopback, denied ports, zero Agent capabilities, replay rejection, cleanup without journal deletion, and preservation of a foreign bridge with the recorded name.
The broader Worker gate ran 45 tests in 17.487 seconds: 43 passed and the two explicitly opted-in native Claude push/PR probes were skipped.
The earlier focused journal and native filter gate passed five tests in 5.525 seconds.
Ruff lint passed for all changed Worker files.
The controller is still an internal primitive; command execution, pinned hostname delivery, linked result reporting, and dedicated restart recovery remain required.
Its lifecycle methods require the existing Run effect lock.

## Historical command and network reconciliation

Plane now accepts the exact retained network permission ID, effect hash, and pinned scope with a historical command observation.
It checks the original command, turn, lease, Worktree, and approval, then derives network consumption from the database.
Completed observations require both original permissions to have been consumed.
Unknown observations retain preparation before either consumption, after command consumption, or after both consumptions.
The existing Run lock serializes network consumption and historical reporting, and the receipt closes both original consumption paths.
Repeated reports return one unchanged receipt.
Changed IDs, hashes, destinations, extra fields, and omission of a consumed network permission are rejected.
Historical observation still works after lease expiry and member access removal because it records prior facts without granting a new effect.
An unknown result requires a later accepted member reply before a new command request.
Normal command results that omit consumed network facts cannot unlock another command; a matching historical receipt can supply those facts.

The full API permission gate passed 87 tests in 36.93 seconds.
The five focused network history cases passed again in 4.19 seconds after adding the normal-result omission check.
These checks use actual Django endpoints, durable permission and event records, and a concurrent consumption/report race.
They do not execute a network command or prove the Worker recovery route.
Ruff lint and formatting checks passed for the four affected Python files.
Generic journal clearance still refuses network records.

## Worker preparation recovery

The command observer now validates retained network facts, removes the verified private resources, records the `removed` phase, and includes exact network identity, hash, and scope in historical reporting.
It checks cancellation before reporting and retains the journal after lost or malformed receipts.
Dedicated clearance requires the exact unchanged record, removed phase, valid result state, and confirmed receipt.
The caller verifies the stopped command container and absent network resources again before clearance.
Normal command recovery keeps its existing boundary and receipt rules.

The native preparation check creates a real configured Docker controller and bridge with a retained command preparation but no command launch.
It verifies resource removal before reporting, exact historical network facts, retained journal after malformed receipt and cancellation, successful receipt retry, and preservation of later Worktree edits.
It uses a controlled Plane client and does not claim paired HTTP delivery or actual network command execution.
The focused preparation and normal-command recovery checks passed in 4.433 seconds.
The broader gate ran 47 tests in 22.396 seconds: 45 passed and two native Claude probes were explicitly skipped because their model opt-in was not set.
Ruff lint and formatting passed for the four affected Worker files.
At this stage, command containers that joined the controller namespace still required immutable identity recording and a matching boundary verifier before recovery could accept them.
The verifier rejected that configuration until the command namespace integration described below.
Code MCP network execution remains disabled.

## Immutable Docker resource IDs

The journal now retains the verified full bridge ID before controller creation and the verified full controller ID before controller start.
These IDs are separate from the deterministic preparation manifest and remain after resource removal.
Binding requires the `starting` phase, correct ordering, a full Docker ID, and an unused identity field.
The configured phase requires both identities; a configured legacy internal record without them is rejected rather than treated as safe execution authority.
Preparation and partial creation remain recoverable without IDs for resources that were not confirmed.
The controller checks recorded IDs during every resource inspection.

The native check compares persisted identities to actual Docker inspect results.
It also creates a replacement bridge with the same name, subnet, and copied ownership labels after cleanup.
Inspection and cleanup reject the different Docker ID and leave the replacement intact until the test removes its own fixture.
Journal checks cover missing IDs at configuration, out-of-order binding, forbidden rebinding, and retention after child-process exit.
The child-process journal checks use synthetic IDs to test persistence; the controller check supplies actual Docker ID evidence.
The focused journal and filter gate passed 16 checks in 6.643 seconds.
The final broader Worker gate ran 47 tests in 23.868 seconds: 45 passed and two native Claude opt-in probes were skipped.
Ruff lint and formatting passed for all four affected files.
At this stage, actual Agent container creation and verification in the retained controller namespace were still required.

## Command container namespace and recovery

The internal launcher now reuses normal Docker creation and Worktree checks with the exact retained controller ID.
Only the matching configured command reservation can pass the retained-record creation check.
The command container has its normal non-root user, zero capabilities, read-only root, Worktree mount, memory and PID limits, and private PID and IPC boundaries.
It uses `container:<controller-ID>` and the `worktree-network-v1` boundary label.
Its full immutable ID is persisted before start.
Authority callbacks run before creation and before start; replay, an existing container, or changed preparation blocks launch.
Command ID binding requires the configured phase and cannot be repeated or replaced.

Recovery now verifies the exact command ID and recorded namespace, even after controller removal.
It retains uncertainty or completed bounded output until Plane confirms the historical observation.
After receipt and repeated identity checks, it removes the exact stopped network command container before journal clearance.
This prevents later normal effects from inheriting the stale namespace.
Unconfirmed creation or replacement blocks recovery rather than inferring execution.

The native checks cover preparation before Agent launch, an actual started command container, revoked authority between create and start, and an actual completed command through the existing bounded Docker supervisor.
They verify zero effective capabilities, denied ports, changed controller rejection, missing namespace authority rejection, replay rejection, retained journal after malformed receipt and cancellation, later source edit preservation, and command container removal after acknowledgement.
These checks use controlled authority and Plane clients; they do not prove paired permission consumption or enable the production Code tool.
The broader gate passed 73 of 85 tests in 75.411 seconds, with 12 explicit native opt-in skips.
The final four network namespace recovery checks passed in 11.069 seconds, including the completed-command variant added after the broader gate.
The focused command ID ordering and rebinding check also passed.
Ruff lint and formatting passed for all affected files.
At this stage, the grant-bound supervisor, pinned hostname delivery, paired HTTP recovery, and complete Stop orchestration were still required.

## Dual-grant bounded command supervisor

The internal executor now validates separate command and linked pinned network grants and stores both exact identities before calling consumption.
It consumes the command first, then the network grant, and checks current permission status, Worktree identity, cancellation, and the same Code reservation before namespace creation, command start, and execution.
The optional `PLANE_AGENT_NETWORK_IMAGE` setting requires an installed immutable controller image ID.
Absent or tagged images are rejected before consumption.
The internal executor uses the existing bounded Docker command supervisor and resource limits.
It stops command descendants, persists valid completion before cleanup and reporting, removes only verified controller resources, and publishes the exact linked network facts with the normal result.
Receipt confirmation and unchanged identities gate removal of the stopped command container and journal clearance.
Stop removes verified resources but keeps the command unknown and retains the journal for historical acknowledgement.

The native executor check uses real Docker networking and command execution with controlled Plane clients.
Its approved command connects to a listening loopback TCP endpoint at the granted port, rejects a different port, checks zero effective capabilities, and writes one Worktree file.
The six modes cover Allow, Deny, lost command-consumption receipt, lost network-consumption receipt, lost result receipt, and cancellation while the command is actually running.
Consumption callbacks verify the complete persisted preparation and the required order.
Lost consumption does not start the command.
Result receipt loss retains completed output, while Stop retains uncertainty and publishes no completion.
Recovery preserves a later human file edit and does not repeat the command.
The focused six-mode executor check passed in 11.852 seconds.
The broader gate ran 94 tests in 93.686 seconds: 82 passed and 12 native opt-in probes were skipped.
The final environment configuration check passed after adding valid immutable network image coverage.
Ruff lint and formatting passed for all affected files.
These are native Docker checks with controlled permission and receipt clients, not paired API consumption evidence.
At this stage, the Code MCP network route and DNS product flow remained unconnected.
The later Code MCP section records the literal-IP route now delivered.
At this stage, paired API execution, receipt-loss recovery, realistic Worker death, and complete Stop orchestration were still required.

## Paired HTTP permission and receipt checks

The new opt-in API and native checks use the real Django HTTP routes, a private member session and registered Worker token, local Git Worktree preparation, PlaneClient, the internal grant executor, and real Docker networking.
They approve separate command and network requests before consuming either and verify the exact linked permission in durable database history.
The actual command connects to a listening approved literal TCP endpoint, rejects another port, and writes one Worktree file.
The normal mode confirms both consumptions, matching network result facts, record clearance, and capacity release after resource settlement.

The loss modes inject an HTTP transport error only after the real view stores network consumption or the completed command result.
Lost network consumption retains preparation and does not execute the command.
Lost result acknowledgement retains bounded completion and preserves a later human file edit through historical reporting.
Both modes keep their occupied slot until historical acknowledgement and verified cleanup.
The API fixture expires the old lease and invokes the production stale task; a new observer identity then reports the original lease and exact retained effect.
Original consumption attempts return 409 after recovery.
These checks use a new observer identity after controlled expiry, not a killed or restarted polling Worker process.
They call the internal executor directly and do not prove native Harness or Code MCP network delivery.

The normal native/API pair passed in 8.565 and 7.20 seconds.
The final expired-lease network-consumption loss pair passed in 3.630 and 3.57 seconds.
The final expired-lease result-loss pair passed in 6.384 and 6.30 seconds.
An initial fixture omitted the required risk description; Plane correctly rejected it with 400, and the fixture now supplies the displayed risk for each request.
Ruff lint and formatting passed for both new test files.
The API stack, native resources, server port, and private credentials were removed after validation.
At this stage, process-death recovery, Allow for Run and Deny through the product route, complete Stop behavior, hostname delivery, and required Harness conformance were still required before Story 3.4 could be complete.

## Paired executor process death

The HTTP fixture now has three crash modes with actual child executor process termination.
For `consume_crash`, Plane stores the network consumption and holds its response while the test kills the executor.
For `result_crash`, Plane stores the completed command result and holds its response before executor termination.
For `running_crash`, the command writes its marker and remains running while the Host executor is killed.
The test confirms that the Docker command remains running after executor death and after its owned Docker client is terminated.

The original preparation or completion record survives the actual process exit.
The API fixture expires the old lease and runs the production stale task without releasing capacity.
A new identity reads the real expired-slot response and calls the normal `reconcile_code_slots` function.
That function stops the retained command container, reports exact historical command and network facts, confirms the receipt, removes verified resources and the record, and releases capacity.
An active command reports uncertainty; a retained completed result reports completion.
Recovery preserves a later human edit and does not replay the command.
The API check verifies that the capacity release event follows the historical receipt and records an absent command container.

The child executor and its Docker client groups belong only to the fixture.
The fixture verifies the Docker client's parent, executable, process group, and start identity before terminating it.
The final running-command check confirms that no owned Docker client group is active after recovery.
Private process input, tokens, and session data remain outside the checkout and are removed after validation.

The consume-crash native/API pair passed in 14.428 and 4.12 seconds.
The completed-result crash pair passed in 6.953 and 6.80 seconds.
The final active-command crash pair passed in 6.665 and 6.46 seconds, including receipt/release ordering and Docker client group settlement.
Ruff lint and formatting passed for both fixture files.
These checks kill the real internal executor process; they do not launch or restart the full polling Worker or a native Harness.
Full polling Worker and Harness restart, Code MCP delivery, hostname approval, and complete product conformance remain required.

## DNS authorization decision

The accepted design does not define permission for the DNS query that prepares pinned destinations.
DNS resolution can send the requested name to a name server, as described by [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035.html#section-2.2).
An Agent can place Run data in a selected hostname, so resolving an unapproved name can disclose that data before connection approval.
This is an inference from the DNS protocol and the Agent-controlled hostname input.
The internal resolver now requires an exact-host authority callback before hostname lookup and checks it again before snapshot delivery.
Unapproved hostname requests fail before the resolver subprocess starts; literal IPs need no DNS operation.
The three resolver and proposal tests pass in 0.030 seconds, including absent and denied authority.
The member has been asked to choose explicit DNS approval followed by pinned connection approval, or a Plane-owned list of preapproved exact DNS hostnames with approval for new names.
Neither option has been accepted yet.
No DNS product policy, wildcard permission, or Host execution exception is inferred from the pending question.
The system resolver helper is not a delivered Code DNS effect; the selected permission flow and Docker transport must be completed before enabling it.

## Code MCP literal-IP delivery

The existing `plane_run_command` tool now accepts optional exact IP and TCP port destinations.
Its strict schema rejects extra fields, Agent-supplied resolution snapshots, empty destination lists, and Boolean ports.
The Worker normalizes literal addresses without starting a resolver process.
Hostname and wildcard requests fail before DNS lookup or any permission request.
The pending DNS decision does not change this boundary.
The session requests exact command approval first, then a separate network grant bound to that unused command.
The bounded executor consumes the two grants only after both decisions allow execution and retains its existing authority, journal, namespace, resource, and receipt checks.
The tool declares its possible external effect with the MCP open-world annotation.
The Code prompt describes separate destination approval.

Six resolver and native MCP checks passed in 5.629 seconds.
These include pending command and network decisions, network Deny without consumption or Docker launch, approved loopback TCP, blocked wrong-port TCP, exact grant consumption order, command results, and verified cleanup.
They retain the normal command-without-network regression.
The broader Code MCP and resolver suite passed 26 checks in 9.314 seconds with two explicit native opt-in skips.
A native Claude invocation passed in 8.964 seconds with one exact tool call, separate command and network `Allow for Run` decisions, actual Docker TCP, matching result publication, and journal clearance.
The native MCP and Claude checks use a controlled permission client; they do not prove paired HTTP MCP delivery or full polling Worker restart.

## Review

### Paired HTTP Code MCP delivery

The new `mcp_allow` fixture mode runs the private Code MCP server with the production CodeToolSession and PlaneClient.
The native client requests one exact command with a pinned literal TCP destination.
The member reads pending permissions and submits both decisions through the real Plane HTTP endpoints.
Before each decision, the check verifies no command container, journal preparation, or output file exists.
The second request binds the displayed pinned scope to the still-unused command grant.
The real Docker command confirms approved TCP, rejects another port, and writes its execution result once.
Plane confirms both grant consumptions and the matching result before capacity release.
The native and API checks passed in 10.385 and 10.43 seconds.

The first run exposed the test HTTP client's default five-second read timeout while waiting for member approval and Docker preparation.
The resulting client disconnect stopped the session before command launch.
The test now uses a bounded sixty-second transport timeout and a thirty-second completion wait.
Worker polling, authority checks, and execution limits were not changed.
Ruff lint and formatting pass for both updated fixtures.
This check does not launch a Harness or a full polling Worker.
The later Deny and pending-network Stop checks add their evidence below.
Paired MCP changed scope, active-command Stop, and polling Worker recovery remain required.
The later receipt-loss checks add their evidence below.

### Paired HTTP Deny and pending-network Stop

The `mcp_deny` mode approves the exact command but rejects its separately requested network grant through the member HTTP endpoint.
MCP returns `denied` with both permission identities.
Both grants remain unused, no command is created, the Worktree output is absent, and Plane records no completed or historical command result.
The native and API checks passed in 17.514 and 7.49 seconds.

The `mcp_stop_pending` mode requests Stop through the member HTTP endpoint after command approval while the network request remains pending.
Plane rejects network permission status with HTTP 409.
The production MCP permission wait returns a tool error and cancels the session before effect preparation.
Both grants remain unused, no command container or journal is created, and no command result is published.
The native and API checks passed in 7.044 and 7.12 seconds.
Both modes verify resource absence before capacity release and check event ordering in Plane.
The Stop command remains pending because these fixtures do not run the full polling Worker.
This does not prove active-command Stop or the complete Run stopped-state transition.
Ruff lint and formatting passed for both fixture files.

### Paired HTTP Code MCP receipt loss

The `mcp_consume_lost` and `mcp_result_lost` modes use the same real MCP and member HTTP approval flow.
The API fixture returns HTTP 503 only after the production view stores the exact network consumption or completed command result.
The tool returns an error, the session stops, and the existing journal keeps the original grants and network identities.
Consumption loss leaves a prepared command with no output and no command launch.
Result loss leaves completed bounded output and permits a later human edit before recovery.
Both checks keep capacity occupied until the old lease is expired through the production stale task and a new observer submits historical settlement.
The observer never runs the command and preserves the later human output edit.
Plane rejects old-lease consumption attempts with HTTP 409 and stores one historical result after verified network cleanup and before journal clearance and capacity release.

The consumption-loss native/API pair passed in 18.553 and 8.42 seconds.
The result-loss pair passed in 10.971 and 11.00 seconds.
Ruff lint and formatting passed for both fixtures.
These checks launch Code MCP but do not launch a Harness or the full polling Worker.
The later polling Worker section adds native Claude completed-result restart evidence.
The remaining Harnesses, active-command Stop, changed destination scope, and the selected DNS permission flow remain required.

### Polling Worker death at completed network result delivery

The general paired HTTP fixture now accepts `command_network` with either command restart mode.
It starts the actual polling Worker, runs native Claude Q&A, hands the follow-up turn to Code, and approves the exact Worktree write.
Claude then calls Code MCP once with the reviewed command and exact literal-IP TCP destination.
The member approves separate command and network requests through the real Plane HTTP endpoints.
The Docker command confirms approved TCP and rejects another port before incrementing its execution counter once.

The fixture holds the result response either before or after Plane persistence and kills the actual polling Worker.
The Host command result and linked network identities remain in the durable journal.
The native check adds a later human source edit, records index bytes and branch HEAD, expires the old lease through the production stale task, and starts a new polling Worker process.
The new Worker reports the original completed result with both matching grants, confirms historical acknowledgement, removes verified command resources, clears the journal, and releases the original capacity reservation.
The execution counter remains one, the human edit and index bytes remain unchanged, and neither branch moves.
Plane retains one historical result and leaves the Run stale without another claim or commit.
The API verifies exactly three requested and consumed grants and capacity release after historical acknowledgement.

The first two runs passed the native Worker checks but exposed the fixture's old two-grant count in the API check.
Both total and consumed grant assertions now include the exact extra network grant.
With those assertions corrected, the after-persistence native/API pair passed in 40.583 and 40.53 seconds.
The before-persistence pair passed in 43.984 and 44.05 seconds.
Ruff lint and formatting passed for both fixtures.
These checks prove native Claude and polling Worker recovery at completed-result delivery, not Worker death before launch or while the network command is active.
The later active-command section adds polling Worker death evidence during execution.
The remaining Harnesses, death before launch, active-command Stop, changed destination scope, and DNS permission delivery remain required.

### Polling Worker death during the network command

The `command_running_crash` mode uses the real polling Worker, native Claude, Code MCP, member decisions, and exact command and network grants.
The reviewed command confirms approved TCP and a denied different port, writes its execution counter, and remains active with a bounded sleep.
The native check verifies the command container is running and the journal remains `command_prepared` before killing the Worker.
It records the owned Docker client's PID, parent, executable, process group, and start identity.
The fixture keeps the original capacity reservation, expires the old lease through the production stale task, and starts a new polling Worker.

The new Worker settles the retained command container and network resources, reports one matching `unknown` historical event with `result: null`, clears the journal after acknowledgement, and releases the original reservation.
Plane verifies three consumed grants, the linked network identity and pinned scope, one historical result, and capacity release after that event.
The execution counter remains one, later human source edits survive, and Git HEAD and index bytes remain unchanged.
The native check confirms the owned Docker client groups are no longer active.
Failure cleanup can terminate only client groups whose recorded start identity still matches and removes only verified fixture network resources.

The native/API pair passed in 79.332 and 69.17 seconds.
Ruff lint and formatting passed for both fixtures.
This proves active-command polling Worker recovery with native Claude; it does not prove active-command Stop or the remaining Harnesses.
The later Stop section adds polling Worker Stop orchestration evidence.
Death before launch, changed destination scope, and the selected DNS permission flow remain required.

### Active network-command Stop

The `command_running_stop` mode uses native Claude, the real polling Worker, Code MCP, exact member approvals, and the actual member Stop endpoint.
It verifies an active command container and one execution-counter write before requesting Stop.
The first end-to-end run exposed a retained-journal block: `CodeTurn.finish()` refused capacity release before the Worker could acknowledge Stop.
The command and network resources stopped, but the unknown command journal remained and the Stop request stayed pending.
The native/API checks failed in 162.380 and 152.21 seconds.

Code completion and restart now share `reconcile_retained_code_effect` for recognized retained command, path, commit, and push records.
The closing Code session stops new tool work and waits for the current tool call to settle.
The shared route stops verified resources, calls the existing effect-specific historical reporter, and retains its receipt-gated journal clearance.
Unknown launch records and missing historical receipts still block capacity release.
The first correction exposed missing Worktree recovery facts in the acquisition slot and failed in 152.222 and 152.07 seconds.
Code completion now supplies the immutable repository, Worktree, branch, and base-commit facts from its Plane claim without changing the slot API contract.

The corrected native/API pair passed in 59.568 and 59.51 seconds.
Plane stores one unknown historical result before capacity release and Stop acknowledgement.
The Run becomes `stopped`, the Stop command is acknowledged, the execution counter remains one, later human edits survive, and branch HEAD remains unchanged.
There is no completed command event, commit, retained command journal, or command container after settlement.
The shared unit gate passed 37 checks in 9.569 seconds with two explicit native opt-in skips.
Four native Docker recovery and Stop regression checks passed in 7.058 seconds.
Ruff lint and formatting passed for the affected production and fixture files.
The later consumption-boundary section adds pre-launch polling Worker evidence.
Remaining work includes the other Harnesses, namespace preparation boundaries, changed destination scope, granted DNS delivery, and visual product checks.

### Polling Worker death after network consumption and before creation

The `command_consume_crash` mode uses the real polling Worker, native Claude, Code MCP, and member HTTP decisions.
The API fixture holds the network-consumption receipt only after the production view stores that exact consumption.
The native check confirms a `command_prepared` journal with network phase `prepared`, no command container, no controller or bridge, and no execution counter.
It kills the original Worker, retains capacity, expires the old lease through the production stale task, and starts a new polling Worker.

The new Worker reports one `unknown` historical result with `result: null` and the original command and consumed network grant facts.
It clears the journal only after Plane confirms the history and releases the original capacity reservation after reconciliation.
The command counter remains absent, later human source edits survive, and index bytes and branch HEAD remain unchanged.
Plane verifies exactly three requested and consumed grants, no normal command result, one historical result, and release after that event.
No command is launched or replayed during recovery.

The native/API pair passed in 58.279 and 48.16 seconds.
Ruff lint and formatting passed for both fixtures.
This proves the stored-consumption boundary before any Docker network creation, not death during namespace creation or configuration.
The remaining Harnesses, namespace preparation boundaries, changed destination scope, granted DNS delivery, and visual product checks remain required.

### Paired HTTP Allow for Run and literal destination changes

The `mcp_run_scope` mode sends four command requests through the private Code MCP server, production CodeToolSession and PlaneClient, and actual member HTTP decisions.
The member approves the first command once and its exact literal-IP TCP destination for the Run.
The second command has different argv and a fresh command permission; its same destination inherits a fresh network permission from the original Run grant without another network decision.
Both real Docker commands confirm approved TCP and write their distinct output files once.

The third request changes the TCP port, and the fourth changes the literal IP address.
Both network requests remain pending for a fresh member decision rather than inheriting the original grant.
The member denies each changed destination; the corresponding command and network grants remain unused and neither output file is created.
The API verifies four exact command/network pairs, the original `allow_run` grant, the inherited `allow_once` child's grant link, four consumed permissions, two matching completed command results, and no result for either denied command.
Capacity release follows the last decision with verified resource absence.

The native/API pair passed in 34.473 and 24.40 seconds.
Ruff lint and formatting passed for both fixtures.
This checks real HTTP Code MCP delivery without launching a Harness or the full polling Worker.
It does not resolve the pending DNS policy or prove a changed DNS snapshot for the same hostname.
The remaining Harnesses, namespace preparation boundaries, revoked authority through the full product route, granted DNS delivery, and visual product checks remain required.

The protected assets are the Worktree, external destinations, Run authority, and bounded Docker capacity.
Only the trusted control container has network administration rights.
The Agent has no firewall access, and the normal command route keeps its network-disabled boundary unless separate exact destination authority is supplied.
API compatibility is preserved for stored legacy scopes without using them as authority for pinned requests.
The scope extension uses existing JSON storage and does not need a database migration.
The reviewed failure cases include changed DNS scope, malformed resolution, changed port, atomic filter reuse, IPv6 control traffic, loopback replies, and Agent firewall modification.
The Code MCP route now exposes separately granted literal-IP TCP access through the existing bounded executor.
Hostname lookup remains unavailable through this route.
The isolated API stack and native network fixtures were removed after validation.

### Code MCP review

- Summary: The route adds separate exact destination approval to the existing command executor and preserves its durable execution boundary.
- Critical issues: None found in the inspected literal-IP route.
- Major issues: Namespace preparation boundaries, the remaining Harnesses, revoked authority through the full product route, and visual product checks still need evidence; the pending DNS policy blocks hostname delivery and changed DNS snapshots.
- Minor issues: None recorded.
- Positive findings: The route reuses the existing resolver validation, command-bound proposal, permission polling, and bounded executor instead of adding a second authority path.
- Questions: The prior DNS authorization and Harness runtime-write questions remain pending.
- Verdict: Continue integration; Story 3.4 remains incomplete.

Ruff lint and formatting passed for all five touched Python files.
The completed tests left no owned network controller, command container, or bridge.
The private MCP servers stopped and ports 8769 and 8811 were free after validation.

## Required integration

Resolve the pending DNS product decision and implement granted DNS resolution inside the selected execution boundary.
Complete granted hostname resolution and snapshot delivery through the execution route.
Verify namespace ownership and filter identity before the Agent starts.
Prove durable preparation, result reporting, restart recovery, and Stop handling through the paired API executor.
Verify the Code MCP effect through paired HTTP and the permission UI.
Prove Allow once, Allow for Run, Deny, scope changes, and failure recovery through the paired HTTP path and all required Harnesses.
These checks are required before Story 3.4 can be complete.

## Native process death during namespace creation

The Docker recovery check now terminates a separate real creation process with exit code 73 immediately after four Docker operations: bridge creation, controller creation, controller start, and filter installation.
The child calls the production `DockerNetworkBoundary.create_configured` method; only the process-death trigger wraps its Docker call.
It does not replace Docker resources, journal storage, namespace validation, or recovery behavior.

Each case retains `command_prepared` and network phase `starting` without creating a command container.
The parent verifies actual bridge and controller presence, running state, and the exact recorded IDs at each interrupted boundary.
Death after bridge or controller creation also checks recovery when the corresponding creation receipt has not yet bound its ID in the journal.
A second creation attempt is rejected instead of replaying the effect.

The existing production command reconciler removes verified resources before historical reporting.
A malformed receipt and cancellation both retain the journal.
Only a valid receipt permits clearance, and later human source edits survive.
The history client is controlled in this native check; this section does not claim full polling Worker or paired HTTP death during namespace creation.
Those product boundaries remain required.

The focused new check passed in 6.807 seconds across all four death points.
The combined preparation, created-command, denied-start, completed-result, and creation-death gate passed five tests in 19.777 seconds.
Ruff lint and formatting passed.
Docker inspection found no remaining owned network controller or bridge after the gate.
The first fixture run failed because its child used a different workspace label from the parent; the child now receives the parent's exact workspace identity.
The failed fixture's sole empty bridge was removed after verifying its exact Run label and absence of attached containers.
No production boundary was weakened.

## Full polling namespace and revoked authority progress

The [latest acceptance evidence](../../reports/test-260929-1847-network-namespace-recovery.md) proves actual polling Worker death after bridge creation and real HTTP Code MCP rejection after repository authority removal.
The remaining three polling namespace checkpoints are unverified because the interrupted check had no terminal result and its retry reached Claude's session limit before Code execution.
Full polling Worker revocation, visual flows, DNS authority, and other Harness conformance remain required.
