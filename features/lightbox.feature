@browser
Feature: Lightbox in the browser
  As a visitor
  I want a click on a tile to open the full post in a lightbox

  Scenario: Opening and closing the lightbox
    Given a category "Healing" exists
    And a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    And "anna" has posted "Short intro. **Full content** is visible only in the lightbox." in category "Healing"
    When I open the wall of "anna" in the browser
    And I click tile 1 in the browser
    Then the lightbox should be visible
    And the lightbox should contain "Full content"
    When I press Escape in the browser
    Then the lightbox should be hidden
    And there should be no JavaScript errors
