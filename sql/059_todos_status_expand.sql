-- Expand dashboard todo status values (Pending, Waiting, Closed).

alter table public.todos
  drop constraint if exists todos_status_check,
  add constraint todos_status_check check (
    status in (
      'Open',
      'In Progress',
      'Pending',
      'Waiting',
      'Complete',
      'Closed'
    )
  );
