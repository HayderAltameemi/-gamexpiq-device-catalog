# GamExpIQ Batch 02 — CPU/GPU/RAM research and safe RAM variants update

## ما الذي أُنجز؟
- تم التحقق من مواصفات Xiaomi 13T و13T Pro و14T Pro من صفحات الشركة الرسمية.
- وُلّدت 3 حقول إضافية من النوع `ram_options_gb`، دون اختيار RAM لجهاز محدد بصورة عشوائية.
- تم الاحتفاظ ببيانات 4 أجهزة و26 حقلاً من Batch 01؛ الملفات المرحّلة أصبحت 4 أجهزة و29 حقلاً.
- بيانات CPU وGPU الموثقة موجودة في `CPU_GPU_RESEARCH_HELD.csv` **للمراجعة فقط**، ولا تُنشر باعتبارها حقولاً Online مستهلكة بالتطبيق.
- **لم يتم تعديل Flutter أو SQLite الأصلية أو GitHub.**

## لماذا لم نضف CPU/GPU؟
محرك `DeviceSpecEnrichment.ingest()` يرفض استقبال `soc` و`gpu` و`ram_gb` من الإنترنت إذا لم يتطابق `model_code` مع نسخة الجهاز. قاعدة الأجهزة الأصلية لا تتضمن معرفات النسخ للأجهزة الثلاثة. تجاوز الشرط قد يخلط المواصفات بين النسخ الإقليمية. كذلك `ram_options_gb` حقل إضافي وليس قيمة `ram_gb` الأساسية؛ لا يرفع اكتمال الحقول الثمانية ولا يعني ظهور RAM الفعلية.

## رفع GitHub (بعد مراجعة الحقوق والملفات)
1. افتح https://github.com/HayderAltameemi/-gamexpiq-device-catalog
2. احتفظ بالملفات المنشورة الموجودة؛ تحقق أن الكتالوج المنشور من Batch 01 يعرض 4 أجهزة و26 حقلاً قبل المتابعة.
3. من مجلد `github_upload/devices` ارفع/استبدل ملفات الأجهزة الثلاثة بنفس الأسماء داخل `devices` في GitHub (GitHub يسمح تعديل ملف عبر القلم، أو Upload files من داخل مجلد devices).
4. بدّل ملف الجذر `index.json` بملف `github_upload/index.json`.
5. تحقق من ظهور `device_count: 4` و`field_count: 29`، وأن كل ملف من الملفات الثلاثة يظهر `ram_options_gb`.
6. اختبر داخل التطبيق زر Update Specifications، لكن لا تتوقع ظهور RAM المحددة أو GPU/CPU من هذه الدفعة.

## حدود الاختبار
- اجتازت البيانات فحص Schema/Identity/Conflicts و8 اختبارات أساسية، مع اختبارات تحقق إضافية للمحتوى المرحل.
- لم يتم فحص تشغيل Flutter على هاتف أو اختبار GitHub بعد النشر.
- `OEM-PUBLIC-REFERENCE` وسم للمصدر وليس موافقة ترخيص لإعادة التوزيع؛ راجع شروط الاستخدام قبل النشر.
- لا تُستخدم أي قيمة هنا لإثبات FPS مدعوم في PUBG.

## المصادر الرسمية
- https://www.mi.com/global/product/xiaomi-13t-leica/specs/
- https://www.mi.com/global/product/xiaomi-13t-pro-leica/specs/
- https://www.mi.com/global/product/xiaomi-14t-pro/specs/
