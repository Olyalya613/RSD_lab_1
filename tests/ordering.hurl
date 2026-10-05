# Collection CAS regression. Real concurrency is in test_concurrency.py.
POST {{host}}/api/travel-plans
Content-Type: application/json
{"title":"Collection CAS regression"}
HTTP 201
[Captures]
plan_id: jsonpath "$.id"

POST {{host}}/api/travel-plans/{{plan_id}}/locations
Content-Type: application/json
{"name":"A"}
HTTP 201
[Captures]
a_id: jsonpath "$.id"
a_version: jsonpath "$.version"

POST {{host}}/api/travel-plans/{{plan_id}}/locations
Content-Type: application/json
{"name":"B"}
HTTP 201
[Captures]
b_id: jsonpath "$.id"

GET {{host}}/api/travel-plans/{{plan_id}}
HTTP 200
[Captures]
order_version: jsonpath "$.order_version"

PUT {{host}}/api/locations/{{a_id}}
Content-Type: application/json
{"visit_order":2,"version":{{a_version}}}
HTTP 400

PUT {{host}}/api/locations/{{a_id}}
Content-Type: application/json
{"visit_order":2,"version":{{a_version}},"order_version":{{order_version}}}
HTTP 200
[Asserts]
jsonpath "$.version" == 2
jsonpath "$.visit_order" == 2

GET {{host}}/api/travel-plans/{{plan_id}}
HTTP 200
[Captures]
current_order: jsonpath "$.order_version"
b_version: jsonpath "$.locations[0].version"
[Asserts]
jsonpath "$.version" == 1
jsonpath "$.locations[0].id" == "{{b_id}}"
jsonpath "$.locations[0].visit_order" == 1
jsonpath "$.locations[1].visit_order" == 2

# A different location uses a fresh row version but a stale collection version.
PUT {{host}}/api/locations/{{b_id}}
Content-Type: application/json
{"visit_order":2,"version":{{b_version}},"order_version":{{order_version}}}
HTTP 409
[Asserts]
jsonpath "$.current_order_version" == {{current_order}}

DELETE {{host}}/api/travel-plans/{{plan_id}}
HTTP 204
