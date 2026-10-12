Feature: Confirming the e-mail address after signing up
  As the site owner
  I want new users to confirm their e-mail address with a link sent by e-mail (SMTP or Mailgun)
  So that every account belongs to a real mailbox

  Scenario: Signing up sends an activation e-mail
    When I sign up with e-mail "anna@example.com", username "anna" and password "S3cret-pass!"
    Then I should be redirected to the page "Sprawdź swoją skrzynkę"
    And the page should contain "anna@example.com"
    And the account "anna@example.com" should be waiting for activation
    And 1 e-mail should have been sent to "anna@example.com"
    And the e-mail should have the subject "Potwierdź swój adres e-mail – Lightworker Social"
    And the e-mail should contain an activation link
    And the e-mail should have an HTML version with the activation link

  Scenario: The activation link activates the account and logs the user in
    Given I signed up with e-mail "anna@example.com" and username "anna"
    When I open the activation link from the e-mail to "anna@example.com"
    Then I should be redirected to the wall of "anna"
    And I should be logged in as "anna@example.com"
    And the account "anna@example.com" should be active

  Scenario: The activation link can be used only once
    Given I signed up with e-mail "anna@example.com" and username "anna"
    And I opened the activation link from the e-mail to "anna@example.com"
    When I log out
    And I open the activation link from the e-mail to "anna@example.com"
    Then I should be redirected to the login page
    And the page should contain "Twoje konto jest już aktywne"

  Scenario: An expired activation link does not work
    Given I signed up with e-mail "anna@example.com" and username "anna"
    When I open the activation link from the e-mail to "anna@example.com" 4 days later
    Then the response status should be 400
    And the page should contain "Ten link aktywacyjny wygasł."
    And the account "anna@example.com" should be waiting for activation

  Scenario: A tampered activation link does not work
    Given I signed up with e-mail "anna@example.com" and username "anna"
    When I open a tampered activation link from the e-mail to "anna@example.com"
    Then the response status should be 400
    And the page should contain "Ten link aktywacyjny jest nieprawidłowy."

  Scenario: Logging in before activation explains what to do
    Given I signed up with e-mail "anna@example.com" and username "anna"
    When I log in with e-mail "anna@example.com" and password "S3cret-pass!"
    Then I should not be logged in
    And the page should contain "To konto nie zostało jeszcze aktywowane."
    And the page should contain a link to resend the activation e-mail

  Scenario: A wrong password does not reveal that the account is waiting for activation
    Given I signed up with e-mail "anna@example.com" and username "anna"
    When I log in with e-mail "anna@example.com" and password "wrong-password"
    Then the page should contain "Nieprawidłowy e-mail lub hasło."
    And the page should not contain "nie zostało jeszcze aktywowane"

  Scenario: Requesting a new activation link
    Given I signed up with e-mail "anna@example.com" and username "anna" 2 minutes ago
    When I request a new activation link for "anna@example.com"
    Then 2 e-mails should have been sent to "anna@example.com"
    When I open the activation link from the e-mail to "anna@example.com"
    Then I should be logged in as "anna@example.com"

  Scenario: New activation links are not sent more often than once a minute
    Given I signed up with e-mail "anna@example.com" and username "anna"
    When I request a new activation link for "anna@example.com"
    Then 1 e-mail should have been sent to "anna@example.com"

  Scenario: Requesting a link for an unknown address does not reveal anything
    When I request a new activation link for "nobody@example.com"
    Then no e-mail should have been sent
    And the page should contain "Jeśli konto z tym adresem czeka na aktywację"

  Scenario: Accounts waiting for activation are not public
    Given I signed up with e-mail "anna@example.com" and username "anna"
    When I visit the wall of "anna"
    Then the response status should be 404

  Scenario Outline: The activation e-mail is written in the language of the visitor
    Given I use the language "<lang>"
    When I sign up with e-mail "anna@example.com", username "anna" and password "S3cret-pass!"
    Then the e-mail should have the subject "<subject>"

    Examples:
      | lang | subject                                           |
      | pl   | Potwierdź swój adres e-mail – Lightworker Social  |
      | en   | Confirm your e-mail address – Lightworker Social  |

  Scenario: The user is told when the SMTP server cannot be reached
    Given the SMTP server is unreachable
    When I sign up with e-mail "anna@example.com", username "anna" and password "S3cret-pass!"
    Then I should be redirected to the page "Sprawdź swoją skrzynkę"
    And the page should contain "Nie udało się wysłać e-maila aktywacyjnego."
    And the page should not contain "Wysłaliśmy link aktywacyjny"
    And the account "anna@example.com" should be waiting for activation
    And no e-mail should have been sent

  @smtp
  Scenario: The activation e-mail is delivered through a real SMTP server
    Given a test SMTP server is running
    When I sign up with e-mail "anna@example.com", username "anna" and password "S3cret-pass!"
    Then the SMTP server should have received an e-mail for "anna@example.com"
    And the received e-mail should contain an activation link

  Scenario: The activation e-mail is delivered through the Mailgun API
    Given a test Mailgun API is running
    When I sign up with e-mail "anna@example.com", username "anna" and password "S3cret-pass!"
    Then I should be redirected to the page "Sprawdź swoją skrzynkę"
    And the page should not contain "Nie udało się wysłać e-maila aktywacyjnego."
    And the Mailgun API should have received an e-mail for "anna@example.com"
    And the Mailgun e-mail should contain an activation link

  Scenario: The user is told when Mailgun rejects the e-mail
    Given the Mailgun API rejects messages
    When I sign up with e-mail "anna@example.com", username "anna" and password "S3cret-pass!"
    Then I should be redirected to the page "Sprawdź swoją skrzynkę"
    And the page should contain "Nie udało się wysłać e-maila aktywacyjnego."
    And the account "anna@example.com" should be waiting for activation

  Scenario Outline: SMTP and Mailgun are configured with environment variables
    Given the environment variables "<variables>"
    Then the e-mail backend should be "<backend>"
    And the e-mail setting "<setting>" should be "<value>"

    Examples:
      | variables                                                   | backend | setting       | value                 |
      | EMAIL_HOST=smtp.example.com                                 | smtp    | EMAIL_PORT    | 587                   |
      | EMAIL_HOST=smtp.example.com                                 | smtp    | EMAIL_USE_TLS | True                  |
      | EMAIL_HOST=smtp.example.com;EMAIL_USE_SSL=1                 | smtp    | EMAIL_PORT    | 465                   |
      | EMAIL_HOST=smtp.example.com;EMAIL_USE_SSL=1                 | smtp    | EMAIL_USE_TLS | False                 |
      | EMAIL_HOST=smtp.example.com;EMAIL_PORT=2525;EMAIL_USE_TLS=0 | smtp    | EMAIL_PORT    | 2525                  |
      | EMAIL_HOST=smtp.example.com;EMAIL_HOST_USER=bot             | smtp    | EMAIL_HOST_USER | bot                 |
      | DEFAULT_FROM_EMAIL=hello@example.com;DEBUG=1                | console | DEFAULT_FROM_EMAIL | hello@example.com |
      | MAILGUN_API_KEY=key;MAILGUN_DOMAIN=mg.example.com           | mailgun | MAILGUN_API_URL | https://api.mailgun.net |
      | MAILGUN_API_KEY=key;MAILGUN_DOMAIN=mg.example.com;MAILGUN_REGION=eu | mailgun | MAILGUN_API_URL | https://api.eu.mailgun.net |
      | MAILGUN_API_KEY=key;MAILGUN_DOMAIN=mg.example.com;EMAIL_HOST=smtp.example.com | mailgun | MAILGUN_DOMAIN | mg.example.com |
      | MAILGUN_API_KEY=key;EMAIL_HOST=smtp.example.com             | smtp    | EMAIL_HOST    | smtp.example.com      |
