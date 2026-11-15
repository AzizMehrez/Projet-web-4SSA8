package tn.esprit.awd.candidature.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

@FeignClient(name = "ms-candidate", url = "${application.clients.candidate-url:}")
public interface CandidateClient {
    @GetMapping("/api/candidates/{id}")
    Candidate get(@PathVariable("id") Long id);

    record Candidate(String firstname, String lastname, String email) {
        public String fullName() {
            return firstname + " " + lastname;
        }
    }
}
