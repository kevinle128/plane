# Intent

Xây @agent trên Plane CE tự host: team mention bot trên work item, Claude Code hoặc Codex trên Mac Mini nhận việc, trả comment/PR — không Plane paid Agents, không LLM trong app. Plane + CLI cùng một Mini; người vào Plane qua Tailscale. Amp để sau.

# Job

Doorbell: đưa work item cho Mini, nhận comment hoặc draft PR mà không rời Plane. Một địa chỉ: Mini. Same-box — worker poll API local, CLI chạy trên Mini, ghi lại qua API local. Tailscale chỉ cho người. Không route theo laptop. Mini ngủ/chết thì web cũng không tới; lỗi còn lại là Plane lên mà worker chết.

# v1 product rules (Must)

- Trigger: @mention trong comment work item; chỉ @Claude và @Codex; ai comment được thì mention được. Không dùng Linear delegate/assign làm trigger chính.
- Plane nouns: @mention → Agent Run; activities prompt/thought/action/response/elicitation/error; states created / in_progress / awaiting / completed / stopping / stopped / failed / stale (5 phút). Reply thread tiếp cùng run.
- UI: card Agent Run trên work item; click mở panel timeline thought/tool **durable đầy đủ** (fork cố ý khỏi Plane ephemeral). Comment chỉ kết luận (response/elicitation/error). Không đổ tool vào Activity log của work item.
- Intent mặc định: Q&A. User bảo implement/fix → escalate code **cùng** Agent Run, một timeline, không card/run thứ hai.
- Cây: Q&A chưa worktree → clone hoặc pull latest GitHub vào mirror riêng (path env cạnh worker, **không bao giờ** checkout deploy Plane); SSH key sẵn trên Mini. Đang implement → trả lời từ **worktree đó**. Host Mini checkout không phải nguồn Q&A.
- Code: docker + nhánh `agent/<issue-id>` + worktree + draft PR (người merge). Không pull origin giữa chừng worktree. Stop giết process/Docker, giữ worktree.
- Sandbox: registry pluggable; v1 chỉ provider docker cho ghi code. Q&A không cần Docker. Q&A đọc code: CLI OS sandbox (Seatbelt / workspace-write).
- Bind repo: project Plane → một git remote; comment override. 0 hoặc >1 → elicitation, chưa bind thì không docker write. Không Mini cwd, không last-used.
- Worker poll Plane API local trên Mini; không webhook/tunnel public.
- Cho phép job song song. RAM: docker chỉ khi code. Đầy thì refuse, không boot thêm docker.
- Plane lên, worker chết → stale 5 phút; không heartbeat riêng. Web Plane tới được = Mini sống.
- CLI auth fail → failed ngay (error activity + comment), không treo container.

# Won't this time

Amp; provider sandbox ngoài docker; webhook/tunnel public; clone Plane EE; agent merge main; dùng folder deploy Plane làm workspace; xóa ephemeral lịch sử tool.

# Open / later

- Trần N concurrent / mem_limit từng container (chỉ “refuse khi đầy”).
- Ai được Stop.
- Tín hiệu Q&A chỉ-issue vs đọc-code (khi nào clone/pull).
- Mirror pull không fast-forward: fail (gợi ý) chưa khóa.
- @mention trùng khi run đang chạy (một session / không spawn).
