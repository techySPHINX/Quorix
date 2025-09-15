erDiagram
    events {
        int id PK
        string name
        text description
        datetime start_date
        datetime end_date
        string location
        float price
        int capacity
        int available_tickets
        int organizer_id FK
        bool is_active
        datetime created_at
        datetime updated_at
    }

    users {
        int id PK
        string email
        string full_name
    }

    bookings {
        int id PK
        int user_id FK
        int event_id FK
        int number_of_tickets
    }

    waitlists {
        int id PK
        int user_id FK
        int event_id FK
        int number_of_tickets
    }

    events }o--|| users : "organized by"
    events ||--o{ bookings : "has"
    events ||--o{ waitlists : "has"