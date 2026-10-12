Feature: Signing up and logging in with e-mail and password
  As a visitor
  I want to create an account and log in with my e-mail address
  So that I can publish posts on my wall

  Scenario: A visitor signs up, confirms the e-mail and lands on their own wall
    When I sign up with e-mail "anna@example.com", username "anna" and password "S3cret-pass!"
    Then I should not be logged in
    When I open the activation link from the e-mail to "anna@example.com"
    Then I should be redirected to the wall of "anna"
    And I should be logged in as "anna@example.com"

  Scenario: Signing up with an e-mail that is already taken
    Given a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    When I sign up with e-mail "ANNA@example.com", username "anna2" and password "S3cret-pass!"
    Then the page should contain "Konto z tym adresem e-mail już istnieje."

  Scenario: A user logs in with e-mail and password
    Given a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    When I log in with e-mail "anna@example.com" and password "S3cret-pass!"
    Then I should be logged in as "anna@example.com"

  Scenario: Login with a wrong password fails
    Given a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    When I log in with e-mail "anna@example.com" and password "wrong-password"
    Then I should not be logged in
    And the page should contain "Nieprawidłowy e-mail lub hasło."

  Scenario: The username cannot be used to log in
    Given a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    When I log in with e-mail "anna" and password "S3cret-pass!"
    Then I should not be logged in

  Scenario: A user logs out
    Given a user "anna" with e-mail "anna@example.com" and password "S3cret-pass!"
    And I am logged in as "anna"
    When I log out
    Then I should not be logged in
