package tn.esprit.awd.candidature.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

@FeignClient(name = "ms-job", url = "${application.clients.job-url:}")
public interface JobClient {
    @GetMapping("/api/jobs/{id}")
    Job get(@PathVariable("id") Long id);

    record Job(String name, Boolean available) {
    }
}
