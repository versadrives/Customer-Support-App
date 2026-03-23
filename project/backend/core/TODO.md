# Fix TemplateSyntaxError: Invalid filter 'add_class'

## Steps:
- [x] 1. Create templatetags/__init__.py
- [x] 2. Create templatetags/form_tags.py with add_class filter
- [x] 3. Edit ticket_form.html: add {% load form_tags %}
- [x] 4. Edit ticket_edit.html: add {% load form_tags %}
- [x] 5. Added panel namespace to core/urls.py
- [ ] 6. Restart Django server
- [ ] 7. Test /panel/tickets/new/

