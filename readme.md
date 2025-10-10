# System Overview



Build a Travel Planner REST API with PostgreSQL that handles concurrent editing of travel plans. Focus on ACID transactions and optimistic locking to prevent data conflicts.



## Core Entities

```

typescriptTravelPlan {
  id: UUID
  title: string
  description?: string
  start_date?: date
  end_date?: date
  budget?: decimal
  currency: string = 'USD'
  is_public: boolean = false
  version: integer = 1  // Optimistic locking
  created_at: timestamp
  updated_at: timestamp
}


Location {
  id: UUID
  travel_plan_id: UUID (FK)
  name: string
  address?: string
  latitude?: decimal
  longitude?: decimal
  visit_order: integer     // Auto-increment on insert
  arrival_date?: timestamp
  departure_date?: timestamp
  budget?: decimal
  notes?: text
  created_at: timestamp
}

```

## Critical API Endpoints

```

# Travel Plans
GET    /api/travel-plans                 # List with pagination
POST   /api/travel-plans                 # Create new plan
GET    /api/travel-plans/{id}            # Get plan with locations
PUT    /api/travel-plans/{id}            # Update with version check
DELETE /api/travel-plans/{id}            # Cascade delete

# Locations (always scoped to plan)
POST   /api/travel-plans/{id}/locations     # Add location (auto-order)
PUT    /api/locations/{id}                 # Update single location
DELETE /api/locations/{id}                 # Delete location

```

## Concurrency Patterns to Implement

* Optimistic Locking for travel\_plans using version field
* Auto-incrementing visit\_order for new locations
* Transaction Isolation for location updates
* Cascade Operations with proper foreign key constraints

## Database Design Requirements

* Use UUIDs for all primary keys
* Auto-assign visit\_order = MAX(visit\_order) + 1 for new locations
* Add proper indexes for query performance
* Implement check constraints for data validity
* Create triggers for auto-updating timestamp fields
* Foreign key constraints with CASCADE deletes

## Success Criteria
* Handle concurrent edits without lost updates
* Location addition works with auto-ordering
* Location updates are atomic and consistent
* All operations complete in <200ms
* Comprehensive test coverage with race condition scenarios



# Testing

```cmd

   hurl --test .\tests\ --variables-file .\tests\variables.properties
```

