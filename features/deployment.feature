Feature: Production deployment
  As the operator of the site
  I want a healthcheck endpoint for Railway

  Scenario: The healthcheck answers when the application and the database work
    When the healthcheck is requested
    Then the response status should be 200
    And the page should contain "ok"
