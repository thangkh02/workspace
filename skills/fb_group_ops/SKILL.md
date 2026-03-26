---
name: fb_group_ops
description: Doc candidates Facebook group, loc bai phu hop, tao nhap comment, chi publish khi da duoc phe duyet hoac group duoc quan ly.
---

# Facebook Group Ops

Muc tieu:
- Doc file data/candidates.json
- Tim toi da 3 bai phu hop nhat
- Tao draft comment ngan gon, tu nhien, lien quan
- Ghi ket qua vao data/drafts.json

Quy tac:
- Neu post khong lien quan den topic_keywords thi bo qua
- Khong tao comment spam
- Khong lap lai comment giua nhieu bai
- Neu approval_required=true thi KHONG duoc tu publish
- Chi duoc publish neu:
  1) approved=true
  hoac
  2) managed=true va auto_submit=true

Output JSON phai co cac truong:
- key
- group_name
- permalink
- matched
- score
- reason
- draft_comment
- managed
- approval_required
- auto_submit
- approved

Score:
- 0.0 den 1.0
- >= 0.75 moi duoc giu lai

Giong van:
- ngan gon
- tu nhien
- khong qua sale
- khong khang dinh nhung dieu khong biet chac