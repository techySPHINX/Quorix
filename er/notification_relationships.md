erDiagram
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

    notification_deliveries {
        int id PK
        int notification_id FK
        int user_id FK
        NotificationChannel channel
        string status
    }

    users {
        int id PK
        string email
    }

    notifications }o--|| users : "belongs to"
    notifications ||--o{ notification_deliveries : "has"