erDiagram
    bookings {
        int id PK
        int user_id FK
        int event_id FK
        datetime booked_at
        int number_of_tickets
        numeric total_price
        BookingStatus status
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

    bookings }o--|| users : "belongs to"
    bookings }o--|| events : "is for"
