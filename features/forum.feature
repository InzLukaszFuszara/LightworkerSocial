Feature: Forum with categories as topics
  As a visitor
  I want to browse posts by category
  So that I can follow the topics I care about

  Background:
    Given a category "Meditation" exists
    And a category "Healing" exists
    And a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    And a user "bob" with e-mail "bob@example.com" and password "S3cret-pass!"

  Scenario: The forum lists the categories as topics
    When I visit the forum
    Then I should see the forum topic "Meditation"
    And I should see the forum topic "Healing"

  Scenario: A topic shows tiles with posts from the walls of all users
    Given "anna" has posted "Anna meditates" in category "Meditation"
    And "bob" has posted "Bob meditates" in category "Meditation"
    And "bob" has posted "Bob heals" in category "Healing"
    When I visit the forum topic "Meditation"
    Then I should see 2 tiles
    And the page should contain "Anna meditates"
    And the page should contain "Bob meditates"
    And the page should not contain "Bob heals"

  Scenario: The forum shows how many posts each topic has
    Given "anna" has posted "One" in category "Healing"
    And "bob" has posted "Two" in category "Healing"
    When I visit the forum
    Then the forum topic "Healing" should have 2 posts
    And the forum topic "Meditation" should have 0 posts

  Scenario: An administrator defines categories in the admin panel
    Given an administrator "admin@example.com" with password "S3cret-pass!"
    And I am logged in as "admin@example.com"
    When I add the category "Astrology" with slug "astrology" in the admin panel
    And I visit the forum
    Then I should see the forum topic "Astrology"
