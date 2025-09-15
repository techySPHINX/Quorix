erDiagram
    waitlists {
        int id PK
        int user_id FK
        int event_id FK
        datetime joined_at
        datetime notified_at
        WaitlistStatus status
        int number_of_tickets
        datetime created_at
        datetime updated_at
    }

    users {
        int id PK
        string email
        string full_name
    }

    events {
        int id PK
        string name
        datetime start_date
    }

    waitlists }o--|| users : "belongs to"
    waitlists }o--|| events : "is for"
