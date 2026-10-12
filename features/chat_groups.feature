Feature: Group conversations with rooms
  As a user
  I want to create group conversations with rooms
  And manage who can take part in them

  Background:
    Given a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    And a user "bob" with e-mail "bob@example.com" and password "S3cret-pass!"
    And a user "carol" with e-mail "carol@example.com" and password "S3cret-pass!"
    And "anna" has created the group "Lightworkers"

  Scenario: The creator is the owner and the group starts with a general room
    When "anna" opens the group "Lightworkers"
    Then "anna" should be the owner of the group
    And the group should have the rooms "Ogólny"

  Scenario: Every group has its own link
    Given "anna" has created the group "Healers"
    Then the groups "Lightworkers" and "Healers" should have different links
    And the link of the group "Lightworkers" should open the group page

  Scenario: Asking to join through the link and approval by the owner
    When "carol" opens the link of the group "Lightworkers"
    Then the page should contain "Poproś o dołączenie"
    When "carol" asks to join the group "Lightworkers"
    Then the page should contain "czeka na akceptację"
    And "anna" should see a join request from "carol"
    And "carol" should not be a member of the group "Lightworkers"
    When "anna" approves the join request of "carol"
    Then "carol" should be a member of the group "Lightworkers"
    And "anna" should see no join requests

  Scenario: The owner rejects a join request
    Given "carol" asks to join the group "Lightworkers"
    When "anna" rejects the join request of "carol"
    Then "carol" should not be a member of the group "Lightworkers"
    When "carol" opens the link of the group "Lightworkers"
    Then the page should contain "Poproś o dołączenie"

  Scenario: The owner adds members by nick
    When "anna" adds "bob" to the group "Lightworkers"
    Then "bob" should be a member of the group "Lightworkers"
    And the group "Lightworkers" should be in the conversations of "bob"

  Scenario: Only the owner manages the group
    Given "anna" adds "bob" to the group "Lightworkers"
    When "bob" adds "carol" to the group "Lightworkers"
    Then the response status should be 403
    When "bob" creates the room "Secret" in the group "Lightworkers"
    Then the response status should be 403

  Scenario: The owner creates rooms that are shown as tabs
    Given "anna" adds "bob" to the group "Lightworkers"
    When "anna" creates the room "Medytacje" in the group "Lightworkers"
    And "bob" opens the group "Lightworkers"
    Then the group should have the rooms "Ogólny, Medytacje"

  Scenario: Messages are separated by room
    Given "anna" adds "bob" to the group "Lightworkers"
    And "anna" creates the room "Medytacje" in the group "Lightworkers"
    When "bob" writes "Hello room" in the room "Medytacje" of the group "Lightworkers"
    Then "anna" should see "Hello room" in the room "Medytacje" of the group "Lightworkers"
    And "anna" should not see "Hello room" in the room "Ogólny" of the group "Lightworkers"

  Scenario: The owner removes a member
    Given "anna" adds "bob" to the group "Lightworkers"
    When "anna" removes "bob" from the group "Lightworkers"
    Then "bob" should not be a member of the group "Lightworkers"
    When "bob" opens the group "Lightworkers"
    Then the response status should be 404

  Scenario: The owner cannot be removed or muted
    Given "anna" adds "bob" to the group "Lightworkers"
    When "anna" removes "anna" from the group "Lightworkers"
    Then the response status should be 403
    When "anna" mutes "anna" in the group "Lightworkers" for 5 minutes
    Then the response status should be 403

  Scenario: A muted member sees the time left and cannot write
    Given "anna" adds "bob" to the group "Lightworkers"
    When "anna" mutes "bob" in the group "Lightworkers" for 15 minutes
    And "bob" opens the group "Lightworkers"
    Then "bob" should see about 15 minutes until the mute ends
    When "bob" writes "Can I talk?" in the room "Ogólny" of the group "Lightworkers"
    Then the response status should be 403
    And the response should tell about 15 minutes until the mute ends

  Scenario: Writing is possible again when the mute expires
    Given "anna" adds "bob" to the group "Lightworkers"
    And "anna" mutes "bob" in the group "Lightworkers" for 5 minutes
    When the mute of "bob" in the group "Lightworkers" expires
    And "bob" writes "I am back" in the room "Ogólny" of the group "Lightworkers"
    Then the message should be accepted

  Scenario: The owner lifts a mute
    Given "anna" adds "bob" to the group "Lightworkers"
    And "anna" mutes "bob" in the group "Lightworkers" for 60 minutes
    When "anna" mutes "bob" in the group "Lightworkers" for 0 minutes
    And "bob" writes "Thanks" in the room "Ogólny" of the group "Lightworkers"
    Then the message should be accepted

  Scenario: A member can leave the group, the owner cannot
    Given "anna" adds "bob" to the group "Lightworkers"
    When "bob" leaves the group "Lightworkers"
    Then "bob" should not be a member of the group "Lightworkers"
    When "anna" leaves the group "Lightworkers"
    Then the response status should be 400

  Scenario Outline: The default room name is translated
    Given "anna" uses the language "<lang>"
    When "anna" opens the group "Lightworkers"
    Then the group should have the rooms "<room>"

    Examples:
      | lang | room    |
      | pl   | Ogólny  |
      | en   | General |
