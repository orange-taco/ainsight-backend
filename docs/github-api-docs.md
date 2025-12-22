### GitHub Search API docs

REST API에는 검색에 대한 사용자 지정 속도 제한이 있습니다. 인증된 요청의 경우 [검색 코드](https://docs.github.com/ko/rest/search/search#search-code) 엔드포인트를 제외한 모든 검색 엔드포인트에 대해 **분당 최대 30개**의 요청를 만들 수 있습니다. 

REST API를 사용하여 찾으려는 특정 항목을 검색할 수 있습니다. 예를 들어 리포지토리에서 사용자 또는 특정 파일을 찾을 수 있습니다. Google에서 검색을 수행하는 방법을 생각해 보세요. 원하는 결과(또는 찾고 있는 몇 가지 결과)를 찾을 수 있도록 설계되었습니다. Google에서 검색하는 것과 마찬가지로 요구 사항에 가장 적합한 항목을 찾을 수 있도록 검색 결과의 몇 페이지를 표시하려는 경우가 있습니다. 요구를 충족하기 위해 GitHub REST API는 **각 검색에 대해 최대 1,000개의 결과**를 제공합니다.

### 속도 제한 초과
기본 요청 제한을 초과하면 403또는 429응답을 받게 되며, x-ratelimit-remaining헤더에는 가 표시됩니다 0. 헤더에 지정된 시간이 경과하기 전까지는 요청을 다시 시도하지 마십시오 x-ratelimit-reset.

보조 요청 제한을 초과하면 응답과 함께 보조 요청 제한 초과를 나타내는 오류 메시지가 표시됩니다. 응답 헤더에 403` request-request-out`이 있는 경우, 해당 헤더에 지정된 시간(UTC 에포크 초)이 경과할 때까지 요청을 재시도하지 마십시오. 헤더가 `request-request-out`인 경우 , 헤더에 지정된 시간(UTC 에포크 초)이 경과할 때까지 요청을 재시도하지 마십시오 . 그렇지 않은 경우, 재시도하기 전에 최소 1분을 기다리십시오. 보조 요청 제한으로 인해 요청이 계속 실패하는 경우, 재시도 간격을 지수적으로 증가시키면서 특정 횟수만큼 재시도한 후 오류를 발생시키십시오.429retry-afterx-ratelimit-remaining0x-ratelimit-reset

사용량 제한이 걸린 상태에서 계속해서 요청을 보내면 연동이 차단될 수 있습니다.


### [**인증된 사용자에 대한 기본 속도 제한**](https://docs.github.com/ko/rest/using-the-rest-api/rate-limits-for-the-rest-api?apiVersion=2022-11-28#primary-rate-limit-for-authenticated-users)

개인 액세스 토큰을 사용하여 API 요청을 할 수 있습니다. 또한 GitHub 앱이나 OAuth 앱을 승인하면 해당 앱이 사용자를 대신하여 API 요청을 할 수 있습니다.

이러한 모든 요청은 시간당 5,000건의 개인 요청 제한에 포함됩니다. GitHub Enterprise Cloud 조직이 소유한 GitHub 앱에서 사용자를 대신하여 수행하는 요청은 시간당 15,000건의 더 높은 요청 제한이 적용됩니다. 마찬가지로, GitHub Enterprise Cloud 조직의 구성원인 경우, GitHub Enterprise Cloud 조직이 소유하거나 승인한 OAuth 앱에서 사용자를 대신하여 수행하는 요청도 시간당 15,000건의 더 높은 요청 제한이 적용됩니다.

### [**`GITHUB_TOKEN`GitHub Actions 의 기본 속도 제한**](https://docs.github.com/ko/rest/using-the-rest-api/rate-limits-for-the-rest-api?apiVersion=2022-11-28#primary-rate-limit-for-github_token-in-github-actions)

GitHub Actions 워크플로에서 요청을 인증하는 데 내장된 기능을 사용할 수 있습니다 `GITHUB_TOKEN`. [워크플로에서 인증에 GITHUB_TOKEN 사용하기를](https://docs.github.com/en/actions/security-guides/automatic-token-authentication) 참조하세요 .

리포지토리당 시간당 요청 제한은 `GITHUB_TOKEN`1,000건입니다. GitHub Enterprise Cloud 계정에 속한 리소스에 대한 요청의 경우, 리포지토리당 시간당 요청 제한은 15,000건입니다.