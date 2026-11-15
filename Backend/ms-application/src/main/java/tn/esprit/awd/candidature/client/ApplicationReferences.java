package tn.esprit.awd.candidature.client;

import feign.FeignException;
import org.springframework.cloud.client.circuitbreaker.CircuitBreakerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

import java.util.function.Supplier;

@Component
public class ApplicationReferences {
    private final CandidateClient candidates;
    private final JobClient jobs;
    private final CircuitBreakerFactory<?, ?> breakers;

    public ApplicationReferences(CandidateClient candidates, JobClient jobs, CircuitBreakerFactory<?, ?> breakers) {
        this.candidates = candidates;
        this.jobs = jobs;
        this.breakers = breakers;
    }

    public CandidateClient.Candidate candidate(Long id) {
        return lookup("ms-candidate", "Candidate", id, () -> candidates.get(id));
    }

    public JobClient.Job job(Long id) {
        JobClient.Job job = lookup("ms-job", "Job", id, () -> jobs.get(id));
        if (job.available() == null) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Job availability is missing");
        }
        return job;
    }

    private <T> T lookup(String service, String resource, Long id, Supplier<T> request) {
        T result = breakers.create(service).run(() -> {
            try {
                T response = request.get();
                if (response == null) {
                    throw new IllegalStateException("Empty response from " + service);
                }
                return response;
            } catch (FeignException.NotFound missing) {
                return null;
            }
        }, failure -> {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, service + " is unavailable", failure);
        });
        if (result == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, resource + " " + id + " was not found");
        }
        return result;
    }
}
