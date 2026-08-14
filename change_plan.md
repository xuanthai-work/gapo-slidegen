# Prompt xây dựng lại Gapo SlideGen

Bạn đang làm việc với ba repository sau:

1. Repository sản phẩm hiện tại:
   `D:\work\Gapo\gapo-slidegen`

2. Presenton:
   `D:\work\Gapo\presenton`
   <https://github.com/presenton/presenton>

3. Presentation AI của ALLWEONE:
   <https://github.com/allweonedev/presentation-ai>

Tôi muốn xóa hướng triển khai hiện tại trong `gapo-slidegen` và xây dựng lại dự án từ đầu.

Tuy nhiên, KHÔNG được xóa file, sửa code, cài dependency, scaffold hoặc bắt đầu implementation ngay. Dự án phải trải qua đầy đủ các giai đoạn discovery, lựa chọn kiến trúc, lập plan, viết specification và phê duyệt trước khi được phép implement.

## 1. Mục tiêu sản phẩm

Xây dựng một website tạo slide/presentation bằng AI với các yêu cầu:

- Là một web app độc lập.
- Người dùng có thể truy cập và dùng thử như một sản phẩm thật.
- UI/UX phải đẹp, nhất quán và đủ hoàn chỉnh để đưa cho người ngoài sử dụng.
- Không được mang cảm giác scaffold, admin template hoặc demo kỹ thuật.
- Người dùng có một workflow rõ ràng từ nhập yêu cầu đến tạo và sử dụng presentation.
- Website phải self-host được.
- Luồng chính phải chạy được mà không bắt buộc sử dụng dịch vụ trả phí.
- Không bắt buộc OpenAI, Gemini, authentication SaaS, database SaaS, storage SaaS hoặc OCR SaaS trả phí.
- Có thể sử dụng phần mềm, thư viện và model mã nguồn mở hoặc chạy local nếu phù hợp.
- Phiên bản đầu tiên phải chạy độc lập trước.
- Việc tích hợp vào website hoặc hệ thống của công ty là giai đoạn sau.
- Kiến trúc cần để ngỏ khả năng tích hợp sau này, nhưng không được làm phức tạp MVP chỉ vì nhu cầu tương lai.

Mục tiêu tối thiểu của sản phẩm:

```text
Người dùng truy cập website
→ đăng nhập hoặc sử dụng theo cơ chế đã thống nhất
→ nhập prompt hoặc nguồn nội dung
→ tạo outline
→ xem và chỉnh outline
→ tạo slides
→ theo dõi tiến trình generation
→ xem và chỉnh presentation
→ lưu presentation
→ trình chiếu hoặc export
→ mở lại presentation sau đó
```

## 2. Ý nghĩa của yêu cầu “không mất phí”

“Không mất phí” được hiểu là:

- Không có dịch vụ trả phí nào là dependency bắt buộc của luồng chính.
- Không bắt buộc dùng API OpenAI, Gemini hoặc AI provider thương mại.
- Không bắt buộc dùng database, authentication, file storage, OCR hoặc hosting SaaS trả phí.
- Có thể chạy toàn bộ hệ thống bằng các thành phần self-host.
- Dịch vụ có free tier không được xem là nền tảng bắt buộc, vì free tier có thể thay đổi.
- Integration trả phí chỉ được phép là tùy chọn và không làm ảnh hưởng chế độ self-host miễn phí.
- Agent phải phân biệt rõ:
  - Phần chạy hoàn toàn offline.
  - Phần self-host nhưng cần Internet để tải model hoặc dependency ban đầu.
  - Phần cần Internet khi sử dụng.
  - Phần tùy chọn có thể tích hợp dịch vụ trả phí sau này.
- Agent phải nói rõ yêu cầu phần cứng cho AI local, bao gồm CPU, RAM, GPU, VRAM và dung lượng lưu trữ.
- Không được tuyên bố “miễn phí” nếu giải pháp thực tế bắt buộc một cloud API có giới hạn hoặc có thể phát sinh phí.
- Phần mềm có thể miễn phí nhưng server, GPU, điện, domain và băng thông vẫn có chi phí vận hành thực tế. Agent phải nêu rõ sự khác biệt này.

## 3. Hai repository tham chiếu bắt buộc

Sản phẩm mới phải được nghiên cứu và xây dựng chủ yếu dựa trên ý tưởng, phương pháp triển khai, technical patterns và technology choices đã được chứng minh trong hai repository:

- Presenton.
- Presentation AI của ALLWEONE.

Định hướng là khoảng 80% giải pháp kiến trúc, workflow, technical patterns, component ideas hoặc technology choices được học hỏi, điều chỉnh hoặc tái sử dụng từ hai repository này.

Khoảng 20% còn lại dành cho:

- Branding và design system riêng.
- Yêu cầu đặc thù của sản phẩm.
- Lớp tích hợp giữa các subsystem.
- Những phần hai repository chưa giải quyết tốt.
- Việc đơn giản hóa để phù hợp với MVP.
- Ranh giới tích hợp với hệ thống công ty trong tương lai.

Con số 80% là định hướng về mức độ tận dụng tri thức và giải pháp có sẵn. Nó không có nghĩa là:

- Phải copy 80% source code.
- Phải merge trực tiếp hai repository.
- Phải chọn một repository làm nền.
- Frontend mặc định lấy từ Presentation AI.
- Backend mặc định lấy từ Presenton.
- Editor mặc định lấy từ một repository cụ thể.
- Tech stack hiện tại trong `gapo-slidegen` phải được giữ lại.

## 4. Quy tắc nghiên cứu hai repository

Agent bắt buộc phải nghiên cứu cả Presenton và Presentation AI trước khi đề xuất kiến trúc hoặc tech stack cuối cùng.

Với mỗi subsystem, agent phải trình bày:

- Presenton đang giải quyết như thế nào.
- Presentation AI đang giải quyết như thế nào.
- Điểm mạnh của từng cách.
- Điểm yếu của từng cách.
- Khả năng self-host hoàn toàn.
- Dependency hoặc dịch vụ bên ngoài.
- Khả năng chạy miễn phí.
- Yêu cầu phần cứng.
- Rủi ro kỹ thuật.
- Rủi ro bảo trì.
- Rủi ro license.
- Khả năng tái sử dụng code.
- Khả năng chỉ tham khảo pattern rồi viết lại.
- Khuyến nghị dành cho sản phẩm mới.
- Những quyết định cần tôi xác nhận.

Các subsystem tối thiểu phải được đánh giá:

- Product workflow.
- Frontend framework.
- Backend architecture.
- Authentication.
- Database.
- File storage.
- AI model/provider/runtime.
- Prompt processing.
- Outline generation.
- Document ingestion.
- OCR.
- Retrieval hoặc memory nếu thực sự cần.
- Slide schema.
- Template/theme system.
- Slide renderer.
- Slide editor.
- State management.
- Streaming/progress.
- Background jobs.
- Present mode.
- Public sharing.
- PPTX/PDF export.
- Docker và self-host deployment.
- Testing.
- Observability.
- UI/UX và design system.

## 5. Không được tự quyết định tech stack

Agent không được tự chọn tech stack dựa trên:

- Folder hoặc code đang tồn tại trong `gapo-slidegen`.
- Sở thích cá nhân của agent.
- Việc một công nghệ đang có sẵn trong repository.
- Việc Presenton hoặc Presentation AI đang sử dụng công nghệ đó.
- Giả định rằng một lựa chọn là “hiển nhiên”.

Không được mặc định sử dụng:

- Next.js.
- React.
- FastAPI.
- Python.
- Node.js.
- PostgreSQL.
- SQLite.
- Prisma.
- SQLAlchemy.
- Neon.
- NextAuth.
- Ollama.
- LM Studio.
- Plate.
- PptxGenJS.
- python-pptx.
- Docker.
- Hoặc bất kỳ công nghệ cụ thể nào khác.

Với mỗi quyết định kỹ thuật lớn, agent phải:

1. Trình bày cách Presenton đang làm.
2. Trình bày cách Presentation AI đang làm.
3. Trình bày phương án kết hợp hoặc viết mới nếu cần.
4. So sánh trade-off.
5. Đưa ra khuyến nghị có lý do.
6. Hỏi tôi lựa chọn hoặc xin tôi xác nhận.
7. Chỉ ghi nhận quyết định vào plan/spec sau khi tôi đồng ý.

Ngay cả khi agent cho rằng một lựa chọn rõ ràng tốt hơn, quyền lựa chọn cuối cùng vẫn thuộc về tôi.

## 6. Các mức độ tái sử dụng

Agent phải phân biệt rõ bốn mức độ sau.

### Mức 1: Tham khảo ý tưởng

Ví dụ:

- Outline-first workflow.
- Cách tổ chức editor.
- Generation progress.
- Theme selection.
- Present mode.
- Dashboard workflow.

Không copy source code.

### Mức 2: Triển khai lại pattern

Ví dụ:

- Provider abstraction.
- Ownership filtering.
- Structured slide schema.
- Autosave.
- Undo/redo.
- SSE streaming.
- Background job lifecycle.

Viết implementation riêng dựa trên pattern đã nghiên cứu.

### Mức 3: Port component hoặc module

Chuyển một phần code có giới hạn từ repository nguồn sang sản phẩm mới, sau đó điều chỉnh API, styling hoặc data model.

Trước khi port phải ghi rõ:

- Repository nguồn.
- File hoặc module nguồn.
- Lý do port thay vì viết lại.
- Thay đổi dự kiến.
- Dependency đi kèm.
- License áp dụng.
- Chi phí bảo trì.
- Cách kiểm thử.

Mức này cần tôi phê duyệt trước.

### Mức 4: Fork hoặc giữ subsystem gần nguyên bản

Chỉ dùng khi một subsystem quá phức tạp để viết lại và việc giữ gần nguyên bản mang lại lợi ích rõ ràng, ví dụ editor hoặc export engine.

Trước khi sử dụng phải trình bày:

- Phạm vi subsystem.
- Boundary với sản phẩm mới.
- Cách authentication và data ownership hoạt động.
- Cách đồng bộ dữ liệu.
- Cách đồng bộ upstream.
- Chi phí bảo trì.
- Rủi ro coupling.
- License và NOTICE.
- Phương án thay thế.

Mức này cần tôi phê duyệt riêng trước khi implement.

## 7. License và attribution

Presenton hiện sử dụng Apache License 2.0.

Presentation AI của ALLWEONE hiện sử dụng MIT License theo repository được tham chiếu.

Trước khi copy code hoặc asset, agent phải:

- Đọc trực tiếp file `LICENSE` và `NOTICE` hiện tại của repository nguồn.
- Kiểm tra license của dependency và asset liên quan.
- Không giả định font, ảnh, icon, template hoặc package enterprise có cùng license với repository.
- Ghi lại provenance của code được port.
- Nêu rõ file nào được copy hoặc sửa.
- Đề xuất cấu trúc `LICENSES` và `NOTICE` cho sản phẩm mới.
- Không sử dụng logo, tên hoặc thương hiệu của hai dự án như thương hiệu của sản phẩm mới.
- Không mô tả code copy là “chỉ tham khảo ý tưởng”.
- Không copy code hoặc asset trước khi tôi phê duyệt mức độ tái sử dụng.

## 8. Nguyên tắc làm việc bắt buộc

1. Không sửa code trước khi plan và spec được duyệt.
2. Không xóa file trước khi có phê duyệt cleanup riêng.
3. Không cài dependency trong giai đoạn discovery và planning.
4. Không chạy migration hoặc thay đổi database.
5. Không scaffold “để thử”.
6. Không dùng code hiện tại làm lý do để tự quyết định kiến trúc.
7. Repository hiện tại chỉ được đọc để hiểu những gì đang tồn tại.
8. Nếu chưa đủ thông tin, phải hỏi tôi.
9. Nếu cần assumption, phải ghi rõ và xin xác nhận.
10. Không hỏi dồn các câu không ảnh hưởng quyết định.
11. Nhóm câu hỏi theo mức độ ưu tiên.
12. Giải thích ngắn gọn tại sao một câu trả lời ảnh hưởng kiến trúc.
13. Không âm thầm mở rộng scope.
14. Không chuyển sang giai đoạn tiếp theo nếu chưa được tôi duyệt rõ ràng.
15. Mọi thay đổi quan trọng sau khi duyệt spec phải được đề xuất lại trước khi thực hiện.

## 9. Quy trình bắt buộc

### Giai đoạn 1: Discovery

Được phép:

- Đọc source và tài liệu của Presenton.
- Đọc source và tài liệu của Presentation AI.
- Đọc `gapo-slidegen` ở chế độ read-only.
- Kiểm tra Git ở chế độ read-only.
- So sánh các workflow và technical patterns.
- Hỏi tôi các câu hỏi làm rõ.

Không được phép:

- Sửa file.
- Xóa file.
- Di chuyển file.
- Cài dependency.
- Scaffold.
- Chạy migration.
- Thay đổi database.
- Copy code.
- Chọn tech stack cuối cùng.
- Viết implementation.
- Tạo UI prototype trong repository.

Agent phải hỏi tôi tối thiểu về:

- Đối tượng người dùng mục tiêu.
- Trải nghiệm sản phẩm mong muốn.
- Mức độ giống Gamma, Canva hoặc PowerPoint.
- Khả năng chỉnh sửa slide cần có.
- Structured editor hay free-form canvas.
- Input bắt buộc: prompt, PDF, DOCX, PPTX, URL hoặc loại khác.
- Export bắt buộc: PPTX, PDF, image hoặc HTML.
- PPTX có cần native editable hay không.
- Authentication: guest, email/password, OAuth hay cách khác.
- Số lượng người dùng thử dự kiến.
- Có cần workspace tách biệt theo user không.
- Có cần public sharing không.
- Có cần collaboration không.
- Ngôn ngữ ưu tiên.
- Mức độ hỗ trợ tiếng Việt.
- Dữ liệu có được phép gửi ra ngoài không.
- Môi trường self-host dự kiến.
- Hệ điều hành máy chủ.
- CPU, RAM, GPU và VRAM có sẵn.
- Tech stack đội phát triển quen thuộc hoặc muốn sử dụng.
- Phần nào trong Presenton người dùng thích.
- Phần nào trong Presentation AI người dùng thích.
- Timeline mong muốn.
- Tiêu chí để đánh giá MVP thành công.

Kết quả của discovery:

- Product brief.
- Target users.
- Core user journey.
- Must-have requirements.
- Nice-to-have requirements.
- Out-of-scope.
- Constraints.
- Assumptions.
- Open questions.
- Danh sách quyết định cần tôi đưa ra.

Sau đó dừng và chờ tôi duyệt discovery.

### Giai đoạn 2: Reference Architecture Assessment

Sau khi discovery được duyệt, agent phải phân tích hai repository theo bảng:

| Subsystem | Presenton | Presentation AI | Viết mới/kết hợp | Khuyến nghị | Cần tôi quyết định |
|---|---|---|---|---|---|
| Product workflow | ... | ... | ... | ... | Có/Không |
| Frontend | ... | ... | ... | ... | Có/Không |
| Backend | ... | ... | ... | ... | Có/Không |
| Authentication | ... | ... | ... | ... | Có/Không |
| Database | ... | ... | ... | ... | Có/Không |
| File storage | ... | ... | ... | ... | Có/Không |
| AI runtime | ... | ... | ... | ... | Có/Không |
| Document processing | ... | ... | ... | ... | Có/Không |
| Slide schema | ... | ... | ... | ... | Có/Không |
| Template system | ... | ... | ... | ... | Có/Không |
| Editor | ... | ... | ... | ... | Có/Không |
| Streaming/jobs | ... | ... | ... | ... | Có/Không |
| Export | ... | ... | ... | ... | Có/Không |
| Deployment | ... | ... | ... | ... | Có/Không |
| UI/UX | ... | ... | ... | ... | Có/Không |

Mỗi khuyến nghị phải ghi mức tái sử dụng:

- Mức 1: tham khảo ý tưởng.
- Mức 2: triển khai lại pattern.
- Mức 3: port module.
- Mức 4: giữ subsystem gần nguyên bản.

Sau bảng tổng quan, phải tạo decision log cho từng quyết định lớn:

- Quyết định cần đưa ra.
- Phương án Presenton.
- Phương án Presentation AI.
- Phương án kết hợp hoặc viết mới.
- Khuyến nghị.
- Lý do.
- Trade-off.
- Yêu cầu phần cứng/vận hành.
- Tác động tới self-host miễn phí.
- Câu hỏi xác nhận dành cho tôi.

Dừng và chờ tôi duyệt từng quyết định quan trọng.

### Giai đoạn 3: Chọn architecture và tech stack

Chỉ sau khi assessment được duyệt:

- Đề xuất 2–3 phương án kiến trúc hoặc tech stack nếu vẫn còn lựa chọn.
- Không tự chọn phương án cuối cùng.
- So sánh:
  - Độ khó phát triển.
  - Thời gian MVP.
  - Khả năng self-host.
  - Khả năng chạy offline.
  - Yêu cầu CPU/RAM/GPU.
  - Chất lượng AI local.
  - Khả năng xây editor.
  - Import/export.
  - Khả năng mở rộng.
  - Khả năng tích hợp với website công ty sau này.
  - Chi phí vận hành thực tế.
  - Rủi ro và giới hạn.
- Đưa ra khuyến nghị nhưng chờ tôi chọn.

Dừng và chờ tôi xác nhận architecture và tech stack.

### Giai đoạn 4: Implementation plan

Sau khi architecture và tech stack được duyệt, viết plan chi tiết gồm:

- Kiến trúc tổng thể.
- Repository structure.
- Các application/service.
- Data flow.
- Authentication flow.
- Ownership model.
- AI generation flow.
- Model runtime.
- Document ingestion nếu nằm trong scope.
- Slide schema.
- Template/theme system.
- Renderer.
- Editor.
- State management.
- Background jobs.
- Progress updates.
- Database.
- File storage.
- Import/export.
- Self-host deployment.
- Security.
- Testing.
- Observability.
- UI/UX direction.
- Các prototype kỹ thuật cần làm trước.
- Các milestone theo vertical slice.
- Acceptance criteria của từng milestone.
- Rủi ro và fallback.

Plan phải ưu tiên vertical slice chạy thật:

```text
Truy cập/đăng nhập
→ tạo presentation
→ tạo outline
→ chỉnh outline
→ generate slides
→ chỉnh sửa
→ lưu
→ trình chiếu/export
→ mở lại
```

Không lập plan theo kiểu làm toàn bộ frontend trước rồi mới nối backend.

Dừng và chờ tôi duyệt plan.

### Giai đoạn 5: Product specification

Chỉ sau khi plan được duyệt, viết specification hoàn chỉnh.

SPEC tối thiểu phải có:

1. Product vision.
2. Target users.
3. Product principles.
4. Core user journeys.
5. Functional requirements.
6. Non-functional requirements.
7. UI/UX requirements.
8. Screen inventory.
9. Editor capabilities.
10. AI workflow.
11. AI model/runtime requirements.
12. Document ingestion nếu có.
13. Slide schema.
14. Theme/template system.
15. Data model.
16. API contracts.
17. Authentication.
18. Ownership và authorization.
19. Storage.
20. Background jobs.
21. Progress/streaming.
22. Import/export.
23. Self-host deployment.
24. Security.
25. Performance targets.
26. Accessibility.
27. Responsive behavior.
28. Loading states.
29. Empty states.
30. Error states.
31. Scope.
32. Non-scope.
33. Milestones.
34. Testing strategy.
35. Acceptance criteria.
36. Open questions.
37. Future integration boundary với website công ty.
38. License và source provenance policy.

Spec phải đủ rõ để một agent khác có thể implement mà không phải tự phát minh các yêu cầu quan trọng.

Sau khi viết spec, dừng lại.

Không implement cho đến khi tôi nói rõ:

> “Spec được duyệt, bắt đầu chuẩn bị cleanup và implementation.”

### Giai đoạn 6: Design direction

Trước khi code toàn bộ UI, agent phải trình bày:

- Product design direction.
- Visual identity.
- Design tokens.
- Typography.
- Color system.
- Spacing system.
- Corner-radius rules.
- Elevation/shadow rules.
- Icon system.
- Screen map.
- Wireframe hoặc mô tả layout từng màn hình.
- Navigation model.
- Component inventory.
- Editor layout.
- Responsive strategy.
- Loading/empty/error states.
- Accessibility requirements.
- Những pattern UI tham khảo từ Presenton.
- Những pattern UI tham khảo từ Presentation AI.
- Những phần thiết kế riêng.

Không được copy nguyên UI của Presenton, Presentation AI, Gamma, Canva hoặc PowerPoint.

Có thể học interaction pattern, nhưng sản phẩm phải có branding và design system riêng.

Dừng và chờ tôi duyệt design direction.

### Giai đoạn 7: Cleanup proposal

Chỉ sau khi plan, spec và design direction được duyệt:

- Kiểm tra Git status ở chế độ read-only.
- Liệt kê file/folder hiện tại.
- Phân loại:
  - Giữ lại.
  - Archive.
  - Viết lại.
  - Xóa.
- Liệt kê chính xác mọi target dự kiến xóa.
- Xác minh đường dẫn tuyệt đối.
- Đề xuất backup, branch hoặc commit checkpoint.
- Giải thích dữ liệu nào có thể mất.
- Không được xóa khi chưa có xác nhận riêng.

Dừng và hỏi tôi phê duyệt cleanup.

Chỉ được xóa sau khi tôi xác nhận rõ danh sách target.

### Giai đoạn 8: Implementation

Chỉ được bắt đầu implementation khi có đủ các phê duyệt:

1. Discovery đã được duyệt.
2. Reference assessment đã được duyệt.
3. Architecture và tech stack đã được duyệt.
4. Plan đã được duyệt.
5. Spec đã được duyệt.
6. Design direction đã được duyệt.
7. Cleanup đã được duyệt.

Trong implementation:

- Làm theo vertical slices.
- Sau mỗi milestone phải chạy test.
- Sau mỗi milestone phải demo được luồng thật tương ứng.
- Không dùng mock data để tuyên bố hoàn thành tính năng.
- Mock chỉ được dùng trong UI prototype và phải được ghi rõ.
- Không coi build thành công là tính năng hoàn thành.
- Không âm thầm thay đổi spec.
- Nếu cần thay đổi scope hoặc kiến trúc, phải đề xuất và xin xác nhận.
- Mọi resource theo user phải có ownership test.
- Mọi màn hình phải có loading, empty, error và success state.
- Không để secret hoặc AI key xuất hiện ở frontend.
- Không tuyên bố self-host thành công nếu README chưa đủ để một người mới cài đặt.
- Không tuyên bố AI miễn phí nếu luồng chính vẫn phụ thuộc cloud API trả phí.

## 10. Yêu cầu UI/UX

Sản phẩm phải trông như một website có thể đưa cho người dùng thật:

- Có visual identity nhất quán.
- Typography, spacing, màu sắc và interaction có chủ đích.
- Dashboard không giống admin template mặc định.
- Luồng tạo presentation đơn giản và dễ hiểu.
- Generation progress phải cho người dùng biết hệ thống đang làm gì.
- Outline editor phải trực quan.
- Slide editor phải tập trung vào presentation canvas.
- Application chrome phải trung tính để nội dung slide nổi bật.
- Có autosave feedback rõ ràng nếu autosave nằm trong scope.
- Có trạng thái lỗi và khả năng retry.
- Responsive cho dashboard và các luồng ngoài editor.
- Editor có thể desktop-first nhưng phải có mobile fallback rõ ràng.
- Có keyboard focus states.
- Có contrast phù hợp.
- Không dùng generic AI-purple gradient nếu chưa được chọn làm branding.
- Không lạm dụng card, pill, shadow hoặc glassmorphism.
- Không dùng ba card giống nhau khắp nơi như một template SaaS phổ thông.
- Không dùng placeholder thiếu chủ đích trong bản nghiệm thu.
- Không để UI kỹ thuật của model/provider chiếm luồng người dùng phổ thông.
- Settings kỹ thuật chỉ xuất hiện nếu thực sự cần và đã được duyệt.

## 11. Definition of Done cho MVP

MVP chỉ hoàn thành khi:

- Có cách self-host toàn bộ hệ thống.
- Không có dịch vụ trả phí bắt buộc.
- Một người mới có thể cài và chạy theo README.
- Có luồng end-to-end thật.
- AI generation chạy bằng phương án miễn phí/self-host đã được duyệt.
- Presentation được lưu và mở lại.
- Người dùng chỉnh sửa được các nội dung đã thống nhất.
- Người dùng reorder slide nếu nằm trong scope.
- Có present mode hoặc export theo spec.
- UI đủ đẹp và nhất quán để đưa cho người ngoài dùng thử.
- Có loading, empty, error và retry states.
- Có test cho các luồng quan trọng.
- Không lộ secret.
- Không lộ dữ liệu giữa người dùng.
- Không có bước cốt lõi nào chỉ hoạt động bằng mock.
- Có hướng dẫn yêu cầu phần cứng và giới hạn AI local.
- Có ghi nhận license/provenance cho code hoặc asset được tái sử dụng.
- Có kế hoạch rõ ràng cho việc tích hợp vào website công ty sau này, nhưng integration đó chưa cần được implement.

## 12. Việc cần làm ngay bây giờ

Hiện tại chỉ thực hiện Giai đoạn 1: Discovery.

Không sửa file.
Không xóa file.
Không di chuyển file.
Không scaffold.
Không cài dependency.
Không chạy migration.
Không thay đổi database.
Không copy code.
Không chọn tech stack cuối cùng.
Không viết implementation.
Không tạo UI trong repository.
Không mặc định giữ bất kỳ phần nào của `gapo-slidegen`.

Hãy bắt đầu bằng:

1. Tóm tắt lại cách bạn hiểu mục tiêu sản phẩm.
2. Xác nhận vai trò của Presenton và Presentation AI:
   - Đây là hai nguồn tham chiếu bắt buộc.
   - Khoảng 80% giải pháp dự kiến được học, chọn lọc hoặc tái sử dụng từ hai repository.
   - Không được tự động merge hoặc copy source.
   - Không được tự quyết định tech stack.
3. Kiểm tra read-only khả năng truy cập ba repository.
4. Nêu những quyết định quan trọng cần tôi tham gia lựa chọn.
5. Hỏi nhóm câu hỏi discovery đầu tiên.
6. Ưu tiên các câu hỏi ảnh hưởng lớn nhất đến:
   - Trải nghiệm sản phẩm.
   - Editor.
   - Input/output.
   - Native editable PPTX.
   - Phần cứng chạy AI miễn phí.
   - Quyền riêng tư dữ liệu.
   - Tech stack và năng lực đội phát triển.
7. Giải thích ngắn gọn tại sao mỗi câu hỏi ảnh hưởng đến kiến trúc.
8. Sau đó dừng và chờ câu trả lời.

Không đề xuất tech stack cuối cùng trong phản hồi đầu tiên.

Nguyên tắc quan trọng nhất:

> Agent phải nghiên cứu, so sánh và đưa ra khuyến nghị dựa trên Presenton và Presentation AI, nhưng quyền lựa chọn cuối cùng đối với từng subsystem, tech stack, phạm vi tái sử dụng, plan, spec, cleanup và implementation thuộc về tôi.
