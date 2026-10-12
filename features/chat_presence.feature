Feature: Messenger side panel – who is online
  As a logged in user
  I want to see who is online grouped by status and search users by nick
  So that I can start a conversation

  Background:
    Given a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    And a user "bob" with e-mail "bob@example.com" and password "S3cret-pass!"
    And a user "carol" with e-mail "carol@example.com" and password "S3cret-pass!"
    And a user "annabel" with e-mail "annabel@example.com" and password "S3cret-pass!"

  Scenario: Online users are listed by status
    Given "bob" is online with status "available"
    And "carol" is online with status "away"
    When "anna" refreshes the messenger
    Then the messenger should list "bob" as "available"
    And the messenger should list "carol" as "away"
    And the messenger should not list "annabel"
    And the messenger should not list "anna"

  Scenario: Users who stopped sending heartbeats are offline
    Given "bob" was last online 5 minutes ago
    When "anna" refreshes the messenger
    Then the messenger should not list "bob"

  Scenario: Changing my status
    When "bob" sets the status "away"
    And "anna" refreshes the messenger
    Then the messenger should list "bob" as "away"
    When "bob" sets the status "available"
    And "anna" refreshes the messenger
    Then the messenger should list "bob" as "available"

  Scenario: Logging out removes the user from the list
    Given "bob" is online with status "available"
    And I am logged in as "bob"
    When I log out
    And "anna" refreshes the messenger
    Then the messenger should not list "bob"

  Scenario: Searching users by nick
    Given "annabel" is online with status "available"
    When "bob" searches the messenger for "ANN"
    Then the search results should be "anna, annabel"
    And the search result "annabel" should have the status "available"
    And the search result "anna" should have the status "offline"

  Scenario: Anonymous visitors cannot use the messenger
    When an anonymous visitor refreshes the messenger
    Then the response status should be 401

  Scenario: The panel is only rendered for logged in users
    When I visit the forum
    Then the page should not contain "chat-panel"
    Given I am logged in as "anna"
    When I visit the forum
    Then the page should contain "chat-panel"
