# Student Record Management System

A responsive dashboard for managing student records. Pure Python (standard library) + SQLite. No installs needed.

## Run
```
python app.py
```
Open **http://localhost:8000**. `students.db` is created automatically with two sample students.

## Pages
| Sidebar item | Route | What it does |
|---|---|---|
| 🏠 Dashboard | `/` | Summary cards, data-flow diagram, CRUD map, recent records |
| 👨‍🎓 Students | `/students` | Card directory of active students |
| ➕ Add Student | `/add` | Form → INSERT, with success/error notification |
| 📋 Student Records | `/records` | Table with search, count, Edit and Delete (archive) |
| 🗃️ Archived Records | `/archived` | Archived students, with Restore |

## Data flow
```
User Input → Frontend Form → Controller/Route → Database INSERT → Success Response → Display Records
             <form POST>     POST /students     INSERT INTO       green toast         SELECT * FROM
                             create_student()   students                              students
```

| Operation | Route | Controller | SQL |
|---|---|---|---|
| POST → INSERT | `POST /students` | `create_student` | `INSERT INTO students` |
| SELECT → DISPLAY | `GET /records` | `render_records` | `SELECT * FROM students` (+ `LIKE` for search) |
| UPDATE → MODIFY | `POST /students/<id>/update` | `update_student` | `UPDATE students SET ...` |
| DELETE → ARCHIVE | `POST /students/<id>/delete` | `delete_student` | `INSERT INTO students_archive` + `DELETE FROM students` (one transaction) |
| Restore | `POST /archive/<n>/restore` | `restore_student` | reverse of archive |

**Archive rule:** a deleted record is copied into `students_archive` (with `deleted_at`) before it leaves the live table, so nothing is permanently lost.

## Evidence checklist
| Required evidence | Where |
|---|---|
| ☐ Working form | Add Student page |
| ☐ Working route/controller | `app.py` → `do_POST()` and `create_student()` |
| ☐ Database record created | `sqlite3 students.db "SELECT * FROM students;"` |
| ☐ Data displayed from database | Student Records table |
| ☐ Success/error feedback | Green / red notifications |
| ☐ Screenshot | See `screenshots/` |
| ☐ Data-flow explanation | Dashboard diagram + this README |

## Demo script (~2 min)
1. **Add Student** → save `2026-003 / Ana Reyes / BSIS` → green notification, row appears in the table.
2. Add the same ID again → red error, your input is kept.
3. **Edit** a record → update notification.
4. **Delete** → confirmation dialog → record moves to **Archived Records**.
5. Show the DB: `sqlite3 students.db "SELECT * FROM students_archive;"`
6. **Restore** → record returns to the list.

## Security
Parameterized SQL (`?` placeholders), all output HTML-escaped, Post/Redirect/Get to prevent duplicate submissions.
