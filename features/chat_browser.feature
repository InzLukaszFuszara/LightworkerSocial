@browser
Feature: Messenger in the browser
  As a logged in user
  I want a floating panel on the right and chat bubbles at the bottom of the page

  Background:
    Given a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    And a user "bob" with e-mail "bob@example.com" and password "S3cret-pass!"
    And a user "carol" with e-mail "carol@example.com" and password "S3cret-pass!"
    And "bob" is online with status "available"
    And "carol" is online with status "away"

  Scenario: The side panel lists online users by status and filters by nick
    When "anna" opens the home page in the browser
    Then the messenger panel should be visible on the right
    And the panel section "available" should list "bob"
    And the panel section "away" should list "carol"
    When I type "car" into the messenger search
    Then the panel section "available" should not list "bob"
    And the panel section "away" should list "carol"
    And there should be no JavaScript errors

  Scenario: Chatting in a bubble at the bottom of the window
    When "anna" opens the home page in the browser
    And I click "bob" in the messenger panel
    Then a chat bubble titled "bob" should be docked at the bottom of the window
    When I type "Hello from the bubble" into the chat bubble and send it
    Then the chat bubble should show the message "Hello from the bubble"
    And "bob" should see the message "Hello from the bubble" from "anna"
    When I close the chat bubble
    Then no chat bubble should be open
    And there should be no JavaScript errors

  Scenario: Group rooms are shown as tabs at the top of the bubble
    Given "anna" has created the group "Lightworkers"
    And "anna" creates the room "Medytacje" in the group "Lightworkers"
    When "anna" opens the link of the group "Lightworkers" in the browser
    Then the chat bubble should show the room tabs "Ogólny, Medytacje"
    When I click the room tab "Medytacje"
    Then the room tab "Medytacje" should be active
    When I open the group settings in the chat bubble
    Then the group settings should show the link of the group "Lightworkers"
    And there should be no JavaScript errors

  Scenario: A muted member sees a countdown
    Given "anna" has created the group "Lightworkers"
    And "anna" adds "bob" to the group "Lightworkers"
    And "anna" mutes "bob" in the group "Lightworkers" for 15 minutes
    When "bob" opens the link of the group "Lightworkers" in the browser
    Then the chat bubble should show the mute countdown
    And the chat bubble input should be disabled
    And there should be no JavaScript errors
