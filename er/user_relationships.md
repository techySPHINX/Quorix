erDiagram
    users {
        int id PK
        string email
        string hashed_password
        string full_name
        UserRole role
        bool is_active
        bool is_superuser
        datetime created_at
        datetime updated_at
        datetime last_login
    }

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

    notifications {
        int id PK
        int user_id FK
        NotificationType type
        NotificationPriority priority
        string title
        text message
        text data
        bool is_read
        datetime read_at
        datetime created_at
        datetime updated_at
    }

    notification_preferences {
        int id PK
        int user_id FK
        bool email_enabled
        bool in_app_enabled
        bool sms_enabled
        bool push_enabled
        bool booking_confirmations
        bool booking_cancellations
        bool event_reminders
        bool waitlist_notifications
        bool payment_updates
        bool event_updates
        bool system_announcements
        bool marketing_emails
        string quiet_hours_start
        string quiet_hours_end
        string timezone
        datetime created_at
        datetime updated_at
    }

    users ||--o{ events : "organizes"
    users ||--o{ bookings : "has"
    users ||--o{ waitlists : "has"
    users ||--o{ notifications : "has"
    users ||--|{ notification_preferences : "has"
