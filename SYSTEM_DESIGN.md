# System Design Notes

Covers the main design decisions — double-booking prevention, leave handling, slot holds, and notification failures.

---

## Double-Booking Prevention

This is handled in two layers because relying on just one felt risky.

At the application level, when a patient confirms a booking, we run `SELECT ... FOR UPDATE` on the appointments table for that doctor/date/time combo. This is PostgreSQL's row-level locking — if two patients try to book the same slot simultaneously, one transaction blocks until the other commits. The losing transaction then sees the new row and gets a "slot taken" error. The lock is only held during the INSERT itself, not during the symptom form or LLM call, so contention stays low.

On top of that, there's a partial unique index at the database level:

```sql
CREATE UNIQUE INDEX idx_no_double_booking
ON appointments (doctor_id, appointment_date, start_time)
WHERE status != 'cancelled';
```

This is the safety net — if the application logic ever gets refactored and someone accidentally skips the lock, Postgres will still reject the duplicate. The app catches the constraint violation and returns a clean error. Belt and suspenders.

---

## Doctor Leave Handling

When an admin marks a doctor on leave, we need to deal with any existing bookings on that date. The flow:

1. Find all `booked` appointments for that doctor on that date
2. Set them all to `cancelled` in one transaction (atomic — if one fails, none go through)
3. Email each affected patient explaining the cancellation

The emails are non-blocking — if SendGrid is down, the cancellation still goes through and the failed email enters the retry queue. Prioritizing data consistency over notifications here.

---

## Slot Holds

There's a window between the patient selecting a slot and actually submitting the symptom form. Without some kind of reservation, another patient could grab the same slot during that window.

So when a patient selects a time, we create a `SlotHold` with a 5-minute TTL. Other patients see that slot as unavailable while the hold is active. If the patient submits, the hold gets deleted and the real appointment is created atomically. If they abandon, a background job cleans up expired holds every 60 seconds.

A few constraints I put in place:
- One hold per patient per doctor — selecting a new slot auto-deletes the previous hold, so patients can't hoard slots
- 5 minutes felt right for filling a symptom form. Worst case with the cleanup interval, a hold lives ~6 minutes
- Holds are purely advisory. The actual concurrency control happens at booking time via `SELECT FOR UPDATE` — the hold just improves UX by hiding unavailable slots

---

## Notification Failures

Email is unreliable. SendGrid goes down, rate limits get hit, networks flake. The system can't break when that happens.

Every outgoing email gets logged in `email_logs` before we attempt to send it. The log has the recipient, subject, body, status, retry count, and any error message. This gives a full audit trail.

If sending fails, a background job picks it up every 5 minutes and retries (up to 3 times). After 3 failures the email stays as `failed` for someone to look into manually.

The key thing: email never blocks the API response. When a patient books, the response comes back immediately with the booking details. If the confirmation email fails, the booking still exists — the patient can see it in their dashboard. Same deal with Google Calendar events — if event creation fails (user hasn't connected, token expired, whatever), we log it and move on. The appointment exists regardless.
