# CS217.R11 – BÀI THỰC HÀNH 2: THIẾT KẾ CƠ SỞ TRI THỨC

**Nhóm 1** · **Đề tài:** Hệ thống tư vấn dinh dưỡng và gợi ý thực đơn  
**Hạn nộp:** 23:59, thứ Bảy, 17/10/2026  
**Căn cứ:** Slide Bài thực hành 2 của giảng viên, đặc biệt các trang 5, 8, 10–23, 25–27; kế thừa nội dung TH1 nhóm đã thực hiện.

> **Cách dùng:** Đây là khuôn mẫu làm việc để nhóm điền, không phải báo cáo hoàn chỉnh. Các dòng có ký hiệu `[ ]` là đầu việc; đánh dấu `[x]` sau khi đã kiểm tra được **sản phẩm cụ thể**. Những quy mô, công cụ và ví dụ minh họa bên dưới là **đề xuất của nhóm**, không phải yêu cầu bắt buộc từ slide.

## A. Những yêu cầu cần tuân thủ

### A1. Đề bài (trang 5)

1. Phân tích các thành phần tri thức.
2. Xác định mối liên hệ giữa các thành phần tri thức.
3. Xây dựng mô hình biểu diễn tri thức của ứng dụng.
4. Tổ chức cơ sở tri thức cụ thể trên máy.

### A2. Tệp phải nộp (trang 25)

- [ ] `CS217_TH2_Nhom1_BaoCao.pdf` — báo cáo **4–6 trang** theo trang 26.
- [ ] `CS217_TH2_Nhom1_PhanCong.pdf` — phân công công việc chi tiết.
- [ ] `CS217_TH2_Nhom1_KnowledgeBase.zip` — các tệp tổ chức CSTT trên máy, mã nguồn kiểm tra nếu có và hướng dẫn chạy.

> Slide yêu cầu nộp **các file** tổ chức CSTT; việc nén thành một ZIP là đề xuất để nộp gọn, cần tuân theo định dạng Moodle cho phép.

### A3. Rubric (trang 27)

| Tiêu chí | Tỷ trọng ghi trên slide | Minh chứng nên có |
|---|---:|---|
| Phân tích thành phần tri thức | 20% | Concepts, attributes, facts, functions, rules, nguồn |
| Xác định mối liên hệ | 20% | Bảng Relations, sơ đồ, ràng buộc |
| Mô hình biểu diễn tri thức | 20% | Mô hình hình thức, ví dụ tri thức, giải thích lựa chọn |
| Tổ chức CSTT trên máy | 30% | File KB hợp lệ, tổ chức khoa học, đọc/truy vấn được, dễ mở rộng |

**Lưu ý:** Trang 27 hiển thị bốn tiêu chí có tổng tỷ trọng 90%, không giải thích 10% còn lại; không tự giả định tiêu chí bổ sung.

---

## B. Khuôn mẫu nội dung báo cáo (4–6 trang)

### Trang 1 — Bìa

**TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN**  
**MÔN: CS217.R11 — CÁC HỆ CƠ SỞ TRI THỨC**  
**BÀI THỰC HÀNH 2: THIẾT KẾ CƠ SỞ TRI THỨC**  
**ĐỀ TÀI: HỆ THỐNG TƯ VẤN DINH DƯỠNG VÀ GỢI Ý THỰC ĐƠN**

| Họ tên | MSSV |
|---|---|
| Võ Hoài Chiều | 24520220 |
| Đoàn Hữu Gia Bình | 24520192 |
| Nguyễn Thái Bảo | 24520173 |
| Bùi Huy Chương | 24520230 |

Giảng viên: **[Điền giảng viên phụ trách lớp thực tế]** · TP.HCM, 10/2026

### Trang 2 — 1. Mở đầu và kết quả TH1 (rút gọn)

**1.1. Giới thiệu:** [4–6 câu nêu hệ thống, đối tượng, mục tiêu, phạm vi TH2].

**1.2. Kết quả thu thập/phân loại tri thức từ TH1:** [1 bảng ngắn gồm tri thức khái niệm, thuộc tính, quan hệ, sự kiện, luật, ràng buộc, kinh nghiệm; chỉ đưa những thứ sẽ đưa vào mô hình].

**1.3. Phạm vi thiết kế:** [Dự kiến loại thực phẩm, món ăn, hồ sơ mẫu, tình huống suy luận. Phân biệt mục tiêu TH2 với xây dựng app hoàn chỉnh].

### Trang 3 — 2. Phân tích các thành phần tri thức (Concepts)

**Bảng C1 — Concepts theo cách trình bày trang 17 slide**

| STT | Nguồn | Concept | Cú pháp | Ví dụ ký hiệu | Attributes | Facts | Rules liên quan |
|---|---|---|---|---|---|---|---|
| 1 | TH1 / nguồn chuẩn | Food | `Food(id)` | `Food(tofu)` | `id`, `name`, `origin` | `origin(tofu, plant)` | R02, R03 |
| 2 | TH1 / nguồn chuẩn | Allergen | `Allergen(id)` | `Allergen(soy)` | `id`, `name` | `containsAllergen(tofu, soy)` | R01 |
| 3 | TH1 / nguồn chuẩn | UserProfile | `UserProfile(id)` | `UserProfile(u01)` | `id`, `diet`, `goal` | `hasAllergy(u01, soy)` | R01–R04 |
| 4 | ... | ... | ... | ... | ... | ... | ... |

**Checklist:**
- [ ] Mọi concept có định nghĩa và định danh duy nhất.
- [ ] Attributes có **tên, kiểu dữ liệu, đơn vị (nếu có), điều kiện hợp lệ**.
- [ ] Phân biệt `Food`, `Dish`, `Meal`, `Menu` và `FoodGroup`, `Nutrient`.
- [ ] Ghi nguồn cho tri thức khoa học; phân biệt dữ liệu minh họa và thông tin đã kiểm chứng.
- [ ] Chỉ đưa concept thực sự được quan hệ, luật hoặc hàm sử dụng.

**Danh mục concept đề xuất:** `Food`, `FoodGroup`, `Nutrient`, `NutrientContent`, `Allergen`, `Dish`, `Meal`, `Menu`, `UserProfile`, `DietPattern`. Có thể rút gọn nếu phạm vi thực hiện nhỏ hơn.

### Trang 4 — 3. Mối liên hệ giữa các thành phần tri thức

**Bảng R1 — Relations, bám mẫu trang 18 slide**

| STT | Relation name | Cú pháp / quan hệ khẳng định | Properties | Quan hệ phủ định / ràng buộc | Bội số |
|---|---|---|---|---|---|
| 1 | `belongsTo` | `belongsTo(Food, FoodGroup)` | Phân loại | [Quy tắc kiểm tra] | N–N |
| 2 | `usesIngredient` | `usesIngredient(Dish, Food)` | Có lượng nguyên liệu | [Quy tắc kiểm tra] | N–N |
| 3 | `containsAllergen` | `containsAllergen(Food, Allergen)` | Dữ liệu an toàn | Không suy ra *không dị ứng* khi chưa có dữ liệu | N–N |
| 4 | `hasAllergy` | `hasAllergy(UserProfile, Allergen)` | Hồ sơ người dùng | [Quy tắc kiểm tra] | N–N |
| 5 | ... | ... | ... | ... | ... |

**Sơ đồ:** [Chèn 1 sơ đồ khái niệm chỉ có tên các concept, hướng quan hệ và bội số quan trọng].

**Checklist:**
- [ ] Mọi Relation ghi rõ kiểu đối tượng đầu vào và đầu ra (domain/range).
- [ ] Phân biệt quan hệ *thuộc nhóm*, *chứa chất*, *chế biến từ*, *dị ứng*, *thuộc thực đơn*.
- [ ] Kiểm tra quan hệ nhiều–nhiều; định nghĩa thuộc tính trung gian khi cần (lượng nguyên liệu, khẩu phần).
- [ ] Không nhầm "chưa biết chứa dị nguyên" với "đã xác nhận không chứa dị nguyên".
- [ ] Mỗi quan hệ quan trọng trên bảng cũng được thể hiện trong mô hình / dữ liệu lưu trữ.

### Trang 5 — 4. Mô hình biểu diễn tri thức

**4.1. Mô hình lựa chọn:** [Tên mô hình và vì sao phù hợp với dinh dưỡng, dữ liệu thuộc tính, quan hệ nhiều–nhiều, luật loại trừ/ưu tiên].

**Ví dụ cách hình thức hóa của nhóm (mở rộng từ gợi ý `(C, Rules)` trang 12, KHÔNG phải công thức bắt buộc trong slide):**  
`K = (C, A, Rel, Facts, Rules, Functions)`.

- `C`: tập khái niệm; `A`: thuộc tính; `Rel`: quan hệ; `Facts`: sự kiện.
- `Rules`: luật suy diễn; `Functions`: hàm tính toán phụ trợ.

**Bảng L1 — Rules, theo mẫu trang 19 slide**

| STT | Mã | Phát biểu tự nhiên | IF/THEN hoặc biểu diễn hình thức | Concept tham gia | Relation tham gia | Nguồn |
|---|---|---|---|---|---|---|
| 1 | R01 | Loại thực phẩm chứa tác nhân gây dị ứng của người dùng | IF `hasAllergy(u,a)` AND `containsAllergen(f,a)` THEN `excluded(u,f,allergy)` | UserProfile, Food, Allergen | hasAllergy, containsAllergen | [nguồn] |
| 2 | R02 | Chế độ thuần chay không phù hợp với món chứa nguyên liệu động vật | IF [các tiền đề đã được xác minh] THEN `excluded(u,d,diet)` | UserProfile, Dish, Food | usesIngredient | [nguồn] |
| 3 | R03 | Ưu tiên ứng viên protein phù hợp | IF `proteinGoal(u)` AND `proteinRich(f)` AND `eligible(u,f)` THEN `preferred(u,f)` | UserProfile, Food | ... | [nguồn] |
| 4 | ... | ... | ... | ... | ... | ... |

**Functions cần định nghĩa (nếu dùng):** `sumNutrient(meal, nutrient)`, `checkConstraints(user, dish)`, `rankCandidates(user, foods)`. Định nghĩa rõ input, output, đơn vị và trường hợp thiếu dữ liệu.

**Checklist:**
- [ ] Mô hình có phát biểu hình thức và lý do lựa chọn.
- [ ] Mỗi luật có ID, tiền đề, kết luận, concept/relations dùng trong luật và nguồn.
- [ ] Phân biệt **ràng buộc cứng** (dị ứng, thực phẩm cần tránh) và **ưu tiên mềm** (sở thích, mục tiêu).
- [ ] Có cách xử lý thông tin thiếu, trường hợp mâu thuẫn và thứ tự ưu tiên luật.
- [ ] Biểu diễn trong bảng **khớp** với tệp lưu trữ thực tế.

### Trang 6 — 5. Tổ chức CSTT lên máy và kết luận

**5.1. Công cụ / định dạng:** [Tên công cụ đã chọn, JSON/Python/Experta hoặc giải pháp tương đương].

**5.2. Tổ chức tệp:** [Sơ đồ cây 8–12 dòng; mỗi tệp có mục đích].

**5.3. Ví dụ lưu trữ:** [Trích 1 sự kiện + 1 luật ở tệp thật, kèm tên tệp].

**5.4. Kiểm chứng:** [Bảng rút gọn gồm truy vấn, kết quả mong đợi, kết quả thực tế và trạng thái PASS/FAIL].

**5.5. Kết luận:** [Kết quả TH2 đã làm; giới hạn; định hướng tác vụ cơ bản cho giai đoạn sau].

**Checklist:**
- [ ] Trình bày tệp tổ chức KB thật, không chỉ sơ đồ dự kiến.
- [ ] Dữ liệu có cấu trúc hợp lệ và nạp được bằng công cụ đã chọn.
- [ ] Có tối thiểu một truy vấn thành công và một tình huống kiểm tra ràng buộc.
- [ ] Có README mô tả cách đọc/nạp dữ liệu.
- [ ] Nêu rõ phần đã thực hiện và phần chưa thực hiện; không nhận đã xây dựng hoàn chỉnh bộ máy suy diễn nếu chưa có.

---

## C. Mẫu tổ chức cơ sở tri thức trên máy

**Lựa chọn khuyến nghị cho thời hạn ngắn:** JSON để lưu khái niệm, quan hệ, sự kiện và luật + Python để kiểm tra định dạng và chạy một số tác vụ/truy vấn tối thiểu. Trang 13–14 slide có ví dụ JSON và Python/Experta, nên đây là cách triển khai phù hợp với ví dụ giảng viên; slide **không bắt buộc** framework cụ thể.

```text
NutritionKB/
├── README.md
├── docs/
│   ├── concepts.md
│   ├── relations.md
│   └── rules.md
├── kb/
│   ├── concepts.json
│   ├── relations.json
│   ├── rules.json
│   ├── foods.json
│   ├── dishes.json
│   └── users_sample.json
├── src/
│   ├── validate_kb.py
│   └── demo_queries.py
├── tests/
│   └── test_cases.md
└── sources/
    └── references.md
```

**Quy ước chung (chốt 13–14/10):**

- Mã định danh dùng ASCII + `snake_case`, ví dụ `soy`, `tofu`, `protein_source`.
- Dùng cùng một tên concept/relationship/field ở bảng, sơ đồ, dữ liệu và mã.
- `foods.json` lưu ID, tên, nhóm, nguyên liệu/nguồn gốc, dị nguyên đã kiểm chứng; hàm lượng dinh dưỡng có đơn vị và nguồn.
- `rules.json` lưu ID luật, priority, tập điều kiện, kết luận, nguồn; tránh để luật tồn tại **chỉ** dưới dạng câu văn trong báo cáo.
- Các trường chưa rõ được biểu diễn là *chưa biết/chưa kiểm chứng*; không tự suy ra `false`.
- Quy tắc kiểm tra dữ liệu tham chiếu: mọi ID dùng trong `facts` phải được khai báo hợp lệ.

**Định nghĩa hoàn thành phần lưu trữ:** tải thư mục trên máy sạch, đọc README, nạp file, chạy kiểm tra định dạng và tái lập ít nhất hai truy vấn minh chứng mà không chỉnh tay dữ liệu.

---
